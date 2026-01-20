// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title TechneAgentWallet V4 - Individual Smart Wallet Model
 * @author Techne Protocol
 * @notice Per-user ledger model - each user's funds tracked individually
 * @dev Features:
 * - Individual balance tracking (no shares!)
 * - Per-user investment tracking per protocol
 * - User can only withdraw their own funds
 * - Agent executes strategies per user config
 * - Full MEV protection (whitelist, cooldown, same-block)
 */

contract TechneAgentWalletV4 is AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ============================================
    // ROLES
    // ============================================
    bytes32 public constant AGENT_ROLE = keccak256("AGENT_ROLE");
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");
    bytes32 public constant WHITELISTED_ROLE = keccak256("WHITELISTED_ROLE");

    // ============================================
    // CONSTANTS
    // ============================================
    uint256 public constant DEPOSIT_COOLDOWN = 5 minutes;
    uint256 public constant MINIMUM_DEPOSIT = 1 * 1e6;  // $1 minimum
    uint256 public constant MAX_SINGLE_WITHDRAW = 100_000 * 1e6;  // $100K per tx
    
    // ============================================
    // STATE - Core Token
    // ============================================
    IERC20 public immutable USDC;
    
    // ============================================
    // STATE - Individual Ledger (NO SHARES!)
    // ============================================
    
    // User's free USDC balance (not yet allocated)
    mapping(address => uint256) public balances;
    
    // User's investments: user -> protocol -> amount
    mapping(address => mapping(address => uint256)) public investments;
    
    // User's total amount invested across all protocols
    mapping(address => uint256) public totalInvested;
    
    // List of protocols user has positions in
    mapping(address => address[]) public userProtocols;
    
    // ============================================
    // STATE - MEV Protection
    // ============================================
    mapping(address => uint256) public lastDepositTime;
    mapping(address => uint256) public lastDepositBlock;
    
    // ============================================
    // STATE - Protocol Whitelist
    // ============================================
    mapping(address => bool) public approvedProtocols;
    address[] public protocolList;
    
    // ============================================
    // STATE - Emergency
    // ============================================
    bool public emergencyMode;

    // ============================================
    // EVENTS
    // ============================================
    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event StrategyExecuted(address indexed user, address indexed protocol, uint256 amount);
    event PositionExited(address indexed user, address indexed protocol, uint256 amount);
    event ProtocolApproved(address indexed protocol, bool approved);
    event EmergencyModeSet(bool enabled);
    event UserWhitelisted(address indexed user);

    // ============================================
    // CONSTRUCTOR
    // ============================================
    constructor(
        address _usdc,
        address _admin,
        address _agent,
        address _guardian
    ) {
        require(_usdc != address(0), "Invalid USDC");
        require(_admin != address(0), "Invalid admin");
        
        USDC = IERC20(_usdc);
        
        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(AGENT_ROLE, _agent != address(0) ? _agent : _admin);
        _grantRole(GUARDIAN_ROLE, _guardian != address(0) ? _guardian : _admin);
    }

    // ============================================
    // MODIFIERS
    // ============================================
    
    modifier onlyWhitelisted() {
        require(
            hasRole(WHITELISTED_ROLE, msg.sender) || hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "Not whitelisted"
        );
        _;
    }
    
    modifier afterCooldown() {
        require(
            block.timestamp >= lastDepositTime[msg.sender] + DEPOSIT_COOLDOWN,
            "Cooldown active"
        );
        _;
    }
    
    modifier notSameBlock() {
        require(
            block.number > lastDepositBlock[msg.sender],
            "Same block protection"
        );
        _;
    }
    
    modifier notEmergency() {
        require(!emergencyMode, "Emergency mode");
        _;
    }

    // ============================================
    // USER FUNCTIONS - Deposit
    // ============================================
    
    /**
     * @notice Deposit USDC to your individual balance
     * @param amount Amount of USDC to deposit (6 decimals)
     */
    function deposit(uint256 amount) 
        external 
        nonReentrant 
        onlyWhitelisted 
        whenNotPaused 
        notEmergency 
    {
        require(amount >= MINIMUM_DEPOSIT, "Below minimum deposit");
        
        // Transfer USDC from user
        USDC.safeTransferFrom(msg.sender, address(this), amount);
        
        // Update user's individual balance
        balances[msg.sender] += amount;
        
        // MEV protection timestamps
        lastDepositTime[msg.sender] = block.timestamp;
        lastDepositBlock[msg.sender] = block.number;
        
        emit Deposited(msg.sender, amount);
    }

    // ============================================
    // USER FUNCTIONS - Withdraw
    // ============================================
    
    /**
     * @notice Withdraw USDC from your free balance
     * @dev Only withdraws from free balance, not from investments
     * @param amount Amount to withdraw
     */
    function withdraw(uint256 amount) 
        external 
        nonReentrant 
        afterCooldown 
        notSameBlock 
    {
        require(amount > 0, "Zero amount");
        require(amount <= MAX_SINGLE_WITHDRAW, "Exceeds max");
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Update balance BEFORE transfer (CEI)
        balances[msg.sender] -= amount;
        
        // Transfer to user
        USDC.safeTransfer(msg.sender, amount);
        
        emit Withdrawn(msg.sender, amount);
    }
    
    /**
     * @notice Withdraw ALL - free balance + exit all positions
     * @dev Pulls from all protocols and sends everything to user
     */
    function withdrawAll() 
        external 
        nonReentrant 
        afterCooldown 
        notSameBlock 
    {
        // First, exit all positions
        address[] memory protocols = userProtocols[msg.sender];
        for (uint256 i = 0; i < protocols.length; i++) {
            address protocol = protocols[i];
            uint256 invested = investments[msg.sender][protocol];
            if (invested > 0) {
                _exitPosition(msg.sender, protocol);
            }
        }
        
        // Now withdraw entire balance
        uint256 total = balances[msg.sender];
        require(total > 0, "Nothing to withdraw");
        
        balances[msg.sender] = 0;
        USDC.safeTransfer(msg.sender, total);
        
        emit Withdrawn(msg.sender, total);
    }

    // ============================================
    // AGENT FUNCTIONS - Execute Strategy
    // ============================================
    
    /**
     * @notice Execute strategy for a specific user
     * @dev Called by backend agent based on user's configuration
     * @param user User whose funds to allocate
     * @param protocol Target DeFi protocol (must be approved)
     * @param amount Amount from user's free balance to invest
     * @param data Encoded call data for the protocol
     */
    function executeStrategy(
        address user,
        address protocol,
        uint256 amount,
        bytes calldata data
    ) 
        external 
        onlyRole(AGENT_ROLE) 
        nonReentrant 
        notEmergency 
        returns (bool success, bytes memory result) 
    {
        require(approvedProtocols[protocol], "Protocol not approved");
        require(balances[user] >= amount, "User has insufficient balance");
        require(amount > 0, "Zero amount");
        
        // Deduct from user's free balance
        balances[user] -= amount;
        
        // Track investment
        if (investments[user][protocol] == 0) {
            userProtocols[user].push(protocol);
        }
        investments[user][protocol] += amount;
        totalInvested[user] += amount;
        
        // Approve exact amount (bounded)
        USDC.forceApprove(protocol, amount);
        
        // Execute protocol call
        (success, result) = protocol.call(data);
        
        // Reset approval
        USDC.forceApprove(protocol, 0);
        
        require(success, "Strategy execution failed");
        
        emit StrategyExecuted(user, protocol, amount);
    }
    
    /**
     * @notice Exit a user's position from a protocol
     * @param user User whose position to exit
     * @param protocol Protocol to exit from
     */
    function exitPosition(
        address user,
        address protocol
    ) 
        external 
        onlyRole(AGENT_ROLE) 
        nonReentrant 
    {
        _exitPosition(user, protocol);
    }
    
    function _exitPosition(address user, address protocol) internal {
        uint256 invested = investments[user][protocol];
        require(invested > 0, "No position");
        
        // For now, assume 1:1 exit (real implementation would call protocol.withdraw)
        // This is simplified - in production you'd call the protocol to get actual balance
        
        // Clear investment record
        investments[user][protocol] = 0;
        totalInvested[user] -= invested;
        
        // Add back to free balance
        balances[user] += invested;
        
        emit PositionExited(user, protocol, invested);
    }

    // ============================================
    // VIEW FUNCTIONS
    // ============================================
    
    /**
     * @notice Get user's total value (free + invested)
     */
    function getUserTotalValue(address user) external view returns (uint256) {
        return balances[user] + totalInvested[user];
    }
    
    /**
     * @notice Get user's free balance (available for withdraw/invest)
     */
    function getUserFreeBalance(address user) external view returns (uint256) {
        return balances[user];
    }
    
    /**
     * @notice Get user's investment in specific protocol
     */
    function getUserInvestment(address user, address protocol) external view returns (uint256) {
        return investments[user][protocol];
    }
    
    /**
     * @notice Get all protocols where user has positions
     */
    function getUserProtocols(address user) external view returns (address[] memory) {
        return userProtocols[user];
    }
    
    /**
     * @notice Check if user can withdraw (cooldown passed)
     */
    function canWithdraw(address user) external view returns (bool available, uint256 timeLeft) {
        uint256 unlockTime = lastDepositTime[user] + DEPOSIT_COOLDOWN;
        if (block.timestamp >= unlockTime) {
            return (true, 0);
        }
        return (false, unlockTime - block.timestamp);
    }
    
    function isWhitelisted(address user) external view returns (bool) {
        return hasRole(WHITELISTED_ROLE, user) || hasRole(DEFAULT_ADMIN_ROLE, user);
    }

    // ============================================
    // ADMIN FUNCTIONS
    // ============================================
    
    function whitelistUser(address user) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(WHITELISTED_ROLE, user);
        emit UserWhitelisted(user);
    }
    
    function removeFromWhitelist(address user) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(WHITELISTED_ROLE, user);
    }
    
    function approveProtocol(address protocol, bool approved) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (approved && !approvedProtocols[protocol]) {
            protocolList.push(protocol);
        }
        approvedProtocols[protocol] = approved;
        emit ProtocolApproved(protocol, approved);
    }
    
    function getApprovedProtocols() external view returns (address[] memory) {
        return protocolList;
    }

    // ============================================
    // EMERGENCY FUNCTIONS
    // ============================================
    
    function setEmergencyMode(bool _emergency) external onlyRole(GUARDIAN_ROLE) {
        emergencyMode = _emergency;
        if (_emergency) {
            _pause();
        } else {
            _unpause();
        }
        emit EmergencyModeSet(_emergency);
    }
    
    function pause() external onlyRole(GUARDIAN_ROLE) {
        _pause();
    }
    
    function unpause() external onlyRole(GUARDIAN_ROLE) {
        _unpause();
    }
}
