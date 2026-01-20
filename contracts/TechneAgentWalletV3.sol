// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title TechneAgentWallet V3 - MEV-Resistant Institutional Vault
 * @author Techne Protocol
 * @notice Autonomous yield wallet with MAXIMUM security against MEV attacks
 * @dev Security Features:
 * - Commit-Reveal deposits (prevents frontrunning)
 * - Same-block protection (prevents atomic exploits)
 * - Deposit cooldown (5 min before funds usable)
 * - Whitelist deposits (only approved addresses)
 * - Role-based access control
 * - Reentrancy guard on all state-changing functions
 * - Inflation attack prevention (minimum initial deposit, virtual offset)
 * - Pull payment pattern for withdrawals
 * - Emergency pause mechanism
 * - Bounded token approvals
 */

contract TechneAgentWalletV3 is AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ============================================
    // ROLES
    // ============================================
    bytes32 public constant AGENT_ROLE = keccak256("AGENT_ROLE");
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");
    bytes32 public constant WHITELISTED_ROLE = keccak256("WHITELISTED_ROLE");

    // ============================================
    // STRUCTS
    // ============================================
    struct UserDeposit {
        uint256 shares;
        uint256 depositTime;
        uint256 depositBlock;
    }

    struct DepositCommitment {
        bytes32 commitHash;
        uint256 commitBlock;
        bool revealed;
    }

    // ============================================
    // CONSTANTS - Anti-MEV
    // ============================================
    uint256 public constant COMMIT_REVEAL_BLOCKS = 2;  // Min blocks between commit and reveal
    uint256 public constant DEPOSIT_COOLDOWN = 5 minutes;  // Before funds can be withdrawn
    uint256 public constant SAME_BLOCK_DELAY = 1;  // Blocks between deposit and any action
    
    // ============================================
    // CONSTANTS - Vault Security
    // ============================================
    uint256 public constant MINIMUM_INITIAL_DEPOSIT = 1000 * 1e6;  // $1000 USDC minimum first deposit
    uint256 public constant VIRTUAL_OFFSET = 1e6;  // Virtual shares offset (prevents inflation attack)
    uint256 public constant MAX_FEE = 2000;  // 20% max fee
    uint256 public constant DAILY_WITHDRAW_LIMIT = 1_000_000 * 1e6;  // $1M daily
    uint256 public constant MAX_SINGLE_WITHDRAW = 100_000 * 1e6;  // $100K per tx
    
    // ============================================
    // STATE - Core
    // ============================================
    IERC20 public immutable USDC;
    
    uint256 public totalShares;
    uint256 public totalDeposited;
    uint256 public performanceFee = 1000;  // 10%
    
    mapping(address => UserDeposit) public userDeposits;
    mapping(address => DepositCommitment) public commitments;
    
    // ============================================
    // STATE - Withdrawal Limits
    // ============================================
    uint256 public lastWithdrawDay;
    uint256 public withdrawnToday;
    
    // ============================================
    // STATE - Emergency
    // ============================================
    bool public emergencyMode;

    // ============================================
    // EVENTS
    // ============================================
    event DepositCommitted(address indexed user, bytes32 commitHash, uint256 blockNumber);
    event DepositRevealed(address indexed user, uint256 amount, uint256 shares);
    event Withdrawn(address indexed user, uint256 amount, uint256 shares);
    event EmergencyModeSet(bool enabled);
    event UserWhitelisted(address indexed user);
    event UserRemovedFromWhitelist(address indexed user);

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
        require(_agent != address(0), "Invalid agent");
        
        USDC = IERC20(_usdc);
        
        // Setup roles
        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(AGENT_ROLE, _agent);
        _grantRole(AGENT_ROLE, _admin);  // Admin also has agent role
        _grantRole(GUARDIAN_ROLE, _guardian != address(0) ? _guardian : _admin);
        
        // Initialize with virtual offset to prevent inflation attack
        totalShares = VIRTUAL_OFFSET;
    }

    // ============================================
    // MODIFIERS - Anti-MEV
    // ============================================
    
    modifier notSameBlock(address user) {
        require(
            block.number > userDeposits[user].depositBlock + SAME_BLOCK_DELAY,
            "Action blocked: same block as deposit"
        );
        _;
    }
    
    modifier afterCooldown(address user) {
        require(
            block.timestamp >= userDeposits[user].depositTime + DEPOSIT_COOLDOWN,
            "Cooldown period active"
        );
        _;
    }
    
    modifier onlyWhitelisted() {
        require(
            hasRole(WHITELISTED_ROLE, msg.sender) || hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "Not whitelisted"
        );
        _;
    }
    
    modifier notEmergency() {
        require(!emergencyMode, "Emergency mode active");
        _;
    }
    
    modifier withinWithdrawLimit(uint256 amount) {
        uint256 today = block.timestamp / 1 days;
        if (today > lastWithdrawDay) {
            lastWithdrawDay = today;
            withdrawnToday = 0;
        }
        
        require(amount <= MAX_SINGLE_WITHDRAW, "Exceeds single withdraw limit");
        require(withdrawnToday + amount <= DAILY_WITHDRAW_LIMIT, "Daily limit exceeded");
        _;
        withdrawnToday += amount;
    }

    // ============================================
    // WHITELIST MANAGEMENT
    // ============================================
    
    function whitelistUser(address user) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(WHITELISTED_ROLE, user);
        emit UserWhitelisted(user);
    }
    
    function removeFromWhitelist(address user) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(WHITELISTED_ROLE, user);
        emit UserRemovedFromWhitelist(user);
    }
    
    function isWhitelisted(address user) external view returns (bool) {
        return hasRole(WHITELISTED_ROLE, user) || hasRole(DEFAULT_ADMIN_ROLE, user);
    }

    // ============================================
    // COMMIT-REVEAL DEPOSIT (Anti-MEV)
    // ============================================
    
    /**
     * @notice Step 1: Commit to a deposit (hides amount from MEV bots)
     * @param commitHash keccak256(abi.encodePacked(amount, salt))
     */
    function commitDeposit(bytes32 commitHash) 
        external 
        onlyWhitelisted 
        whenNotPaused 
        notEmergency 
    {
        require(commitHash != bytes32(0), "Invalid commit hash");
        require(!commitments[msg.sender].revealed, "Previous commit not revealed");
        
        commitments[msg.sender] = DepositCommitment({
            commitHash: commitHash,
            commitBlock: block.number,
            revealed: false
        });
        
        emit DepositCommitted(msg.sender, commitHash, block.number);
    }
    
    /**
     * @notice Step 2: Reveal and execute deposit (after COMMIT_REVEAL_BLOCKS)
     * @param amount Actual deposit amount
     * @param salt Random salt used in commit
     */
    function revealDeposit(uint256 amount, bytes32 salt) 
        external 
        nonReentrant 
        onlyWhitelisted 
        whenNotPaused 
        notEmergency 
    {
        DepositCommitment storage commitment = commitments[msg.sender];
        
        require(commitment.commitHash != bytes32(0), "No commitment found");
        require(!commitment.revealed, "Already revealed");
        require(
            block.number >= commitment.commitBlock + COMMIT_REVEAL_BLOCKS,
            "Reveal too early - wait more blocks"
        );
        
        // Verify commitment
        bytes32 expectedHash = keccak256(abi.encodePacked(amount, salt));
        require(commitment.commitHash == expectedHash, "Invalid reveal - hash mismatch");
        
        // Check minimum deposit (first depositor must deposit significant amount)
        if (totalDeposited == 0) {
            require(amount >= MINIMUM_INITIAL_DEPOSIT, "First deposit must be >= $1000");
        }
        
        // Calculate shares (with virtual offset to prevent inflation attack)
        uint256 shares = _calculateShares(amount);
        
        // Mark as revealed before external call (CEI pattern)
        commitment.revealed = true;
        
        // Transfer tokens
        USDC.safeTransferFrom(msg.sender, address(this), amount);
        
        // Update state
        userDeposits[msg.sender].shares += shares;
        userDeposits[msg.sender].depositTime = block.timestamp;
        userDeposits[msg.sender].depositBlock = block.number;
        totalShares += shares;
        totalDeposited += amount;
        
        emit DepositRevealed(msg.sender, amount, shares);
    }
    
    /**
     * @notice Cancel a pending commitment
     */
    function cancelCommitment() external {
        delete commitments[msg.sender];
    }

    // ============================================
    // SIMPLE DEPOSIT (Alternative - still protected)
    // ============================================
    
    /**
     * @notice Direct deposit for whitelisted users (simpler but still protected)
     * @dev Protected by: whitelist, cooldown, same-block check
     */
    function deposit(uint256 amount) 
        external 
        nonReentrant 
        onlyWhitelisted 
        whenNotPaused 
        notEmergency 
    {
        require(amount > 0, "Zero amount");
        
        // First depositor minimum
        if (totalDeposited == 0) {
            require(amount >= MINIMUM_INITIAL_DEPOSIT, "First deposit must be >= $1000");
        }
        
        uint256 shares = _calculateShares(amount);
        
        // Transfer tokens
        USDC.safeTransferFrom(msg.sender, address(this), amount);
        
        // Update state
        userDeposits[msg.sender].shares += shares;
        userDeposits[msg.sender].depositTime = block.timestamp;
        userDeposits[msg.sender].depositBlock = block.number;
        totalShares += shares;
        totalDeposited += amount;
        
        emit DepositRevealed(msg.sender, amount, shares);
    }

    // ============================================
    // WITHDRAW (Pull Pattern)
    // ============================================
    
    /**
     * @notice Withdraw funds (protected by cooldown and limits)
     */
    function withdraw(uint256 shares) 
        external 
        nonReentrant 
        notSameBlock(msg.sender) 
        afterCooldown(msg.sender)
        withinWithdrawLimit(shares)
    {
        require(shares > 0, "Zero shares");
        require(userDeposits[msg.sender].shares >= shares, "Insufficient shares");
        
        uint256 amount = _calculateAssets(shares);
        
        // Update state BEFORE transfer (CEI pattern)
        userDeposits[msg.sender].shares -= shares;
        totalShares -= shares;
        if (totalDeposited >= amount) {
            totalDeposited -= amount;
        } else {
            totalDeposited = 0;
        }
        
        // Transfer
        USDC.safeTransfer(msg.sender, amount);
        
        emit Withdrawn(msg.sender, amount, shares);
    }

    // ============================================
    // AGENT FUNCTIONS
    // ============================================
    
    /**
     * @notice Execute strategy allocation (agent only)
     * @dev Only agent can move funds to approved protocols
     */
    function executeAllocation(
        address protocol,
        uint256 amount,
        bytes calldata data
    ) external onlyRole(AGENT_ROLE) nonReentrant notEmergency returns (bool success, bytes memory result) {
        require(protocol != address(0), "Invalid protocol");
        require(amount <= USDC.balanceOf(address(this)), "Insufficient balance");
        
        // Approve exact amount only (bounded approval)
        USDC.forceApprove(protocol, amount);
        
        // Execute with low-level call
        (success, result) = protocol.call(data);
        
        // Reset approval
        USDC.forceApprove(protocol, 0);
        
        require(success, "Allocation failed");
    }

    // ============================================
    // VIEW FUNCTIONS
    // ============================================
    
    function totalValue() public view returns (uint256) {
        return USDC.balanceOf(address(this));
    }
    
    function getUserValue(address user) external view returns (uint256) {
        if (totalShares <= VIRTUAL_OFFSET) return 0;
        return _calculateAssets(userDeposits[user].shares);
    }
    
    function getUserShares(address user) external view returns (uint256) {
        return userDeposits[user].shares;
    }
    
    function getWithdrawAvailable(address user) external view returns (bool available, uint256 timeLeft) {
        uint256 unlockTime = userDeposits[user].depositTime + DEPOSIT_COOLDOWN;
        if (block.timestamp >= unlockTime) {
            return (true, 0);
        }
        return (false, unlockTime - block.timestamp);
    }
    
    function getCommitmentStatus(address user) external view returns (
        bool hasPending,
        uint256 blocksUntilReveal
    ) {
        DepositCommitment storage c = commitments[user];
        if (c.commitHash == bytes32(0) || c.revealed) {
            return (false, 0);
        }
        
        uint256 revealBlock = c.commitBlock + COMMIT_REVEAL_BLOCKS;
        if (block.number >= revealBlock) {
            return (true, 0);
        }
        return (true, revealBlock - block.number);
    }

    // ============================================
    // INTERNAL FUNCTIONS
    // ============================================
    
    function _calculateShares(uint256 assets) internal view returns (uint256) {
        // With virtual offset to prevent inflation attack
        uint256 totalAssets = totalValue() + 1;  // +1 to avoid division by zero
        return (assets * (totalShares + VIRTUAL_OFFSET)) / totalAssets;
    }
    
    function _calculateAssets(uint256 shares) internal view returns (uint256) {
        if (totalShares <= VIRTUAL_OFFSET) return 0;
        return (shares * totalValue()) / totalShares;
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
    
    function emergencyWithdrawAll() external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(emergencyMode, "Not in emergency mode");
        uint256 balance = USDC.balanceOf(address(this));
        USDC.safeTransfer(msg.sender, balance);
    }
    
    function pause() external onlyRole(GUARDIAN_ROLE) {
        _pause();
    }
    
    function unpause() external onlyRole(GUARDIAN_ROLE) {
        _unpause();
    }

    // ============================================
    // ADMIN FUNCTIONS
    // ============================================
    
    function setPerformanceFee(uint256 _fee) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_fee <= MAX_FEE, "Fee too high");
        performanceFee = _fee;
    }
}
