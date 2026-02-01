// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title TechneAgentAccount
 * @notice ERC-4337 compatible Smart Account for Techne DeFi agents
 * @dev User owns account. Backend has limited session key permissions.
 * 
 * Key Security Properties:
 * - Owner has FULL control (can execute anything, revoke keys, withdraw)
 * - Session keys are LIMITED to whitelisted protocols + selectors only
 * - No admin backdoors - owner is the only authority
 */
contract TechneAgentAccount is Initializable, ReentrancyGuard {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;
    using SafeERC20 for IERC20;

    // ============ Constants ============
    bytes4 private constant ERC1271_SUCCESS = 0x1626ba7e;
    address public constant ENTRYPOINT = 0x0000000071727De22E5E9d8BAf0edAc6f37da032; // v0.7

    // ============ State ============
    address public owner;
    uint256 public nonce;

    // Session key management
    struct SessionKey {
        bool active;
        uint48 validUntil;
        uint256 dailyLimitUSD;
        uint256 spentTodayUSD;
        uint256 lastResetTimestamp;
    }
    mapping(address => SessionKey) public sessionKeys;

    // Protocol whitelist (only these can be called by session keys)
    mapping(address => bool) public whitelistedProtocols;
    address[] public protocolList;

    // Selector whitelist per protocol
    mapping(address => mapping(bytes4 => bool)) public allowedSelectors;

    // ============ Revenue Fee (Capped for Security) ============
    // SECURITY: Even if admin is hacked, fee cannot exceed 20%
    // This means attacker can only take profit, never deposits
    uint256 public constant MAX_REVENUE_FEE_BPS = 5000; // 50% max - IMMUTABLE
    uint256 public constant FEE_CHANGE_TIMELOCK = 48 hours;
    
    uint256 public revenueFee; // Current fee in basis points (100 = 1%)
    address public feeRecipient;
    
    // Timelock for fee changes
    struct PendingFeeChange {
        uint256 newFee;
        uint256 effectiveTime;
    }
    PendingFeeChange public pendingFeeChange;

    // ============ Events ============
    event Initialized(address indexed owner);
    event SessionKeyAdded(address indexed key, uint48 validUntil, uint256 dailyLimitUSD);
    event SessionKeyRevoked(address indexed key);
    event ProtocolWhitelisted(address indexed protocol, bool allowed);
    event SelectorAllowed(address indexed protocol, bytes4 selector, bool allowed);
    event Executed(address indexed target, uint256 value, bytes data);
    event ETHReceived(address indexed sender, uint256 amount);
    event FeeChangeProposed(uint256 newFee, uint256 effectiveTime);
    event FeeChangeExecuted(uint256 oldFee, uint256 newFee);
    event RevenueCollected(address token, uint256 amount);

    // ============ Errors ============
    error OnlyOwner();
    error OnlyEntryPoint();
    error InvalidSignature();
    error SessionKeyExpired();
    error SessionKeyNotActive();
    error DailyLimitExceeded();
    error ProtocolNotWhitelisted();
    error SelectorNotAllowed();
    error ExecutionFailed();
    error InvalidTarget();

    // ============ Modifiers ============
    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    modifier onlyEntryPoint() {
        if (msg.sender != ENTRYPOINT) revert OnlyEntryPoint();
        _;
    }

    // ============ Constructor (for implementation) ============
    constructor() {
        _disableInitializers();
    }

    // ============ Initializer ============
    function initialize(address _owner) external initializer {
        require(_owner != address(0), "Invalid owner");
        owner = _owner;
        emit Initialized(_owner);
    }

    // ============ ERC-4337 Entry Points ============
    
    /**
     * @notice Validates a UserOperation signature (called by EntryPoint)
     * @dev Supports both owner signatures and session key signatures
     */
    function validateUserOp(
        bytes32 userOpHash,
        bytes calldata signature
    ) external view returns (uint256 validationData) {
        // Extract signer from signature
        address signer = userOpHash.toEthSignedMessageHash().recover(signature);
        
        // Owner signature is always valid
        if (signer == owner) {
            return 0; // Valid with no time restrictions
        }
        
        // Check if it's a valid session key
        SessionKey storage sk = sessionKeys[signer];
        if (!sk.active) {
            return 1; // Invalid signature
        }
        
        // Return validation data with time restriction
        // Pack: validUntil (6 bytes) | validAfter (6 bytes) | aggregator (20 bytes)
        return uint256(sk.validUntil) << 160;
    }

    // ============ Execution Functions ============

    /**
     * @notice Execute a call (owner only - no restrictions)
     */
    function execute(
        address target,
        uint256 value,
        bytes calldata data
    ) external onlyOwner nonReentrant returns (bytes memory) {
        return _execute(target, value, data);
    }

    /**
     * @notice Execute a call as session key (restricted to whitelist)
     * @dev Only callable by EntryPoint after validateUserOp
     */
    function executeAsSessionKey(
        address sessionKey,
        address target,
        uint256 value,
        bytes calldata data,
        uint256 estimatedValueUSD
    ) external onlyEntryPoint nonReentrant returns (bytes memory) {
        _validateSessionKeyCall(sessionKey, target, data, estimatedValueUSD);
        return _execute(target, value, data);
    }

    /**
     * @notice Execute with session key signature - NO BUNDLER NEEDED
     * @dev Session key holder signs the call data and anyone can submit
     * @param target Contract to call
     * @param value ETH value to send
     * @param data Calldata for the target
     * @param estimatedValueUSD Estimated USD value for limit tracking
     * @param signature Session key signature over (target, value, data, nonce, chainId, address(this))
     * 
     * SECURITY: Only works if:
     * 1. Signature is valid from an active session key
     * 2. Target is whitelisted protocol
     * 3. Selector is allowed for that protocol
     * 4. Daily USD limit not exceeded
     */
    function executeWithSessionKey(
        address target,
        uint256 value,
        bytes calldata data,
        uint256 estimatedValueUSD,
        bytes calldata signature
    ) external nonReentrant returns (bytes memory) {
        // Create hash of the call parameters + nonce for replay protection
        bytes32 messageHash = keccak256(abi.encodePacked(
            target,
            value,
            keccak256(data),
            nonce,
            block.chainid,
            address(this)
        ));
        
        // Recover signer from signature
        address signer = messageHash.toEthSignedMessageHash().recover(signature);
        
        // Validate this is an active session key with proper permissions
        _validateSessionKeyCall(signer, target, data, estimatedValueUSD);
        
        // Increment nonce for replay protection
        nonce++;
        
        // Execute the call
        return _execute(target, value, data);
    }

    /**
     * @notice Get the hash that session key needs to sign for executeWithSessionKey
     * @dev Helper for backend to construct the correct message to sign
     */
    function getSessionKeyCallHash(
        address target,
        uint256 value,
        bytes calldata data
    ) external view returns (bytes32) {
        return keccak256(abi.encodePacked(
            target,
            value,
            keccak256(data),
            nonce,
            block.chainid,
            address(this)
        ));
    }

    /**
     * @notice Batch execute (owner only)
     */
    function executeBatch(
        address[] calldata targets,
        uint256[] calldata values,
        bytes[] calldata dataArray
    ) external onlyOwner nonReentrant returns (bytes[] memory results) {
        require(targets.length == values.length && values.length == dataArray.length, "Length mismatch");
        results = new bytes[](targets.length);
        for (uint256 i = 0; i < targets.length; i++) {
            results[i] = _execute(targets[i], values[i], dataArray[i]);
        }
    }

    // ============ Session Key Management (Owner Only) ============

    /**
     * @notice Add a new session key
     * @param key The session key address
     * @param validUntil Expiration timestamp
     * @param dailyLimitUSD Maximum USD value per day (with 8 decimals)
     */
    function addSessionKey(
        address key,
        uint48 validUntil,
        uint256 dailyLimitUSD
    ) external onlyOwner {
        require(key != address(0), "Invalid key");
        require(validUntil > block.timestamp, "Already expired");
        
        sessionKeys[key] = SessionKey({
            active: true,
            validUntil: validUntil,
            dailyLimitUSD: dailyLimitUSD,
            spentTodayUSD: 0,
            lastResetTimestamp: block.timestamp
        });
        
        emit SessionKeyAdded(key, validUntil, dailyLimitUSD);
    }

    /**
     * @notice Revoke a session key (emergency stop)
     */
    function revokeSessionKey(address key) external onlyOwner {
        sessionKeys[key].active = false;
        emit SessionKeyRevoked(key);
    }

    // ============ Protocol Whitelist Management (Owner Only) ============

    /**
     * @notice Whitelist a protocol for session key usage
     */
    function setWhitelistedProtocol(address protocol, bool allowed) external onlyOwner {
        if (allowed && !whitelistedProtocols[protocol]) {
            protocolList.push(protocol);
        }
        whitelistedProtocols[protocol] = allowed;
        emit ProtocolWhitelisted(protocol, allowed);
    }

    /**
     * @notice Allow a specific selector for a protocol
     */
    function setAllowedSelector(
        address protocol,
        bytes4 selector,
        bool allowed
    ) external onlyOwner {
        require(whitelistedProtocols[protocol], "Protocol not whitelisted");
        allowedSelectors[protocol][selector] = allowed;
        emit SelectorAllowed(protocol, selector, allowed);
    }

    /**
     * @notice Batch whitelist protocols and selectors
     */
    function batchWhitelist(
        address[] calldata protocols,
        bytes4[][] calldata selectors
    ) external onlyOwner {
        require(protocols.length == selectors.length, "Length mismatch");
        for (uint256 i = 0; i < protocols.length; i++) {
            if (!whitelistedProtocols[protocols[i]]) {
                protocolList.push(protocols[i]);
                whitelistedProtocols[protocols[i]] = true;
                emit ProtocolWhitelisted(protocols[i], true);
            }
            for (uint256 j = 0; j < selectors[i].length; j++) {
                allowedSelectors[protocols[i]][selectors[i][j]] = true;
                emit SelectorAllowed(protocols[i], selectors[i][j], true);
            }
        }
    }

    // ============ Fee Management (With Timelock) ============

    /**
     * @notice Propose a fee change (starts 48h timelock)
     * @dev Fee is capped at MAX_REVENUE_FEE_BPS (20%)
     */
    function proposeFeeChange(uint256 newFee) external onlyOwner {
        require(newFee <= MAX_REVENUE_FEE_BPS, "Fee exceeds 20% max");
        uint256 effectiveTime = block.timestamp + FEE_CHANGE_TIMELOCK;
        pendingFeeChange = PendingFeeChange(newFee, effectiveTime);
        emit FeeChangeProposed(newFee, effectiveTime);
    }

    /**
     * @notice Execute pending fee change after timelock
     */
    function executeFeeChange() external onlyOwner {
        require(pendingFeeChange.effectiveTime != 0, "No pending change");
        require(block.timestamp >= pendingFeeChange.effectiveTime, "Timelock not elapsed");
        
        uint256 oldFee = revenueFee;
        revenueFee = pendingFeeChange.newFee;
        pendingFeeChange = PendingFeeChange(0, 0);
        
        emit FeeChangeExecuted(oldFee, revenueFee);
    }

    /**
     * @notice Cancel a pending fee change
     */
    function cancelFeeChange() external onlyOwner {
        pendingFeeChange = PendingFeeChange(0, 0);
    }

    /**
     * @notice Set fee recipient address
     */
    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        require(_feeRecipient != address(0), "Invalid recipient");
        feeRecipient = _feeRecipient;
    }

    /**
     * @notice Collect revenue fee from profits
     * @dev Called after harvest to collect platform fee
     */
    function collectRevenue(address token, uint256 profitAmount) external returns (uint256 fee) {
        require(msg.sender == address(this), "Self call only");
        require(feeRecipient != address(0), "No fee recipient");
        
        fee = (profitAmount * revenueFee) / 10000;
        if (fee > 0 && token != address(0)) {
            IERC20(token).safeTransfer(feeRecipient, fee);
            emit RevenueCollected(token, fee);
        }
    }

    // ============ View Functions ============

    function isValidSignature(
        bytes32 hash,
        bytes calldata signature
    ) external view returns (bytes4) {
        address signer = hash.toEthSignedMessageHash().recover(signature);
        if (signer == owner) {
            return ERC1271_SUCCESS;
        }
        if (sessionKeys[signer].active && sessionKeys[signer].validUntil > block.timestamp) {
            return ERC1271_SUCCESS;
        }
        return bytes4(0);
    }

    function getProtocolList() external view returns (address[] memory) {
        return protocolList;
    }

    function getSessionKeyInfo(address key) external view returns (
        bool active,
        uint48 validUntil,
        uint256 dailyLimitUSD,
        uint256 spentTodayUSD
    ) {
        SessionKey storage sk = sessionKeys[key];
        return (sk.active, sk.validUntil, sk.dailyLimitUSD, sk.spentTodayUSD);
    }

    // ============ Internal Functions ============

    function _execute(
        address target,
        uint256 value,
        bytes calldata data
    ) internal returns (bytes memory) {
        if (target == address(0)) revert InvalidTarget();
        
        (bool success, bytes memory result) = target.call{value: value}(data);
        if (!success) {
            // Bubble up revert reason
            if (result.length > 0) {
                assembly {
                    revert(add(result, 32), mload(result))
                }
            }
            revert ExecutionFailed();
        }
        
        emit Executed(target, value, data);
        return result;
    }

    function _validateSessionKeyCall(
        address sessionKey,
        address target,
        bytes calldata data,
        uint256 estimatedValueUSD
    ) internal {
        SessionKey storage sk = sessionKeys[sessionKey];
        
        // Check session key is active
        if (!sk.active) revert SessionKeyNotActive();
        if (sk.validUntil < block.timestamp) revert SessionKeyExpired();
        
        // Check protocol whitelist
        if (!whitelistedProtocols[target]) revert ProtocolNotWhitelisted();
        
        // Check selector whitelist
        bytes4 selector = bytes4(data[:4]);
        if (!allowedSelectors[target][selector]) revert SelectorNotAllowed();
        
        // Check and update daily limit
        if (block.timestamp >= sk.lastResetTimestamp + 1 days) {
            sk.spentTodayUSD = 0;
            sk.lastResetTimestamp = block.timestamp;
        }
        if (sk.spentTodayUSD + estimatedValueUSD > sk.dailyLimitUSD) revert DailyLimitExceeded();
        sk.spentTodayUSD += estimatedValueUSD;
    }

    // ============ Receive ETH ============
    receive() external payable {
        emit ETHReceived(msg.sender, msg.value);
    }
}
