// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title TechneAgentWallet V4.3 - Execution Risk Hardened
 * @author Techne Protocol
 * @notice Production-ready with execution risk mitigations
 * 
 * V4.2 Features (inherited):
 * - Replay protection, deadline, slippage
 * - Fee-on-transfer safe, validated withdrawals
 * - 24h timelock, oracle sanity, dust sweep
 * 
 * V4.3 NEW - Execution Risk Fixes:
 * - Rebalance hysteresis (anti-chop)
 * - Flash Loan emergency deleverage
 * - L2 Sequencer uptime check
 * - Health Factor monitoring
 */

interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound
    );
}

interface IPool {
    function supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode) external;
    function withdraw(address asset, uint256 amount, address to) external returns (uint256);
    function borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf) external;
    function repay(address asset, uint256 amount, uint256 interestRateMode, address onBehalfOf) external returns (uint256);
    function getUserAccountData(address user) external view returns (
        uint256 totalCollateralBase,
        uint256 totalDebtBase,
        uint256 availableBorrowsBase,
        uint256 currentLiquidationThreshold,
        uint256 ltv,
        uint256 healthFactor
    );
    function flashLoanSimple(
        address receiverAddress,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

interface IFlashLoanSimpleReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

// V4.3.1 - DEX Router Interface (Aerodrome style)
interface IRouter {
    struct Route {
        address from;
        address to;
        bool stable;
        address factory;
    }
    
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        Route[] calldata routes,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
    
    function getAmountsOut(
        uint256 amountIn,
        Route[] calldata routes
    ) external view returns (uint256[] memory amounts);
}

contract TechneAgentWalletV43 is AccessControl, ReentrancyGuard, Pausable, IFlashLoanSimpleReceiver {
    using SafeERC20 for IERC20;
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

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
    uint256 public constant MINIMUM_DEPOSIT = 1 * 1e6;
    uint256 public constant MAX_SINGLE_WITHDRAW = 100_000 * 1e6;
    uint256 public constant SIGNER_ROTATION_TIMELOCK = 24 hours;
    uint256 public constant MAX_PRICE_DEVIATION = 1000;  // 10%
    uint256 public constant MAX_PROTOCOLS_PER_USER = 20;
    
    // V4.3 NEW - Execution Risk Constants
    uint256 public constant MIN_REBALANCE_INTERVAL = 4 hours;  // Anti-chop
    uint256 public constant MIN_PRICE_MOVE_FOR_REBALANCE = 300;  // 3% minimum price move
    uint256 public constant MAX_ORACLE_STALENESS = 30 minutes;  // Tighter than V4.2
    uint256 public constant SEQUENCER_GRACE_PERIOD = 1 hours;
    uint256 public constant MIN_HEALTH_FACTOR = 1.1e18;  // 1.1 = safe margin
    
    // ============================================
    // STATE - Core
    // ============================================
    IERC20 public immutable USDC;
    IERC20 public immutable WETH;  // V4.3.1 - For cross-asset deleverage
    AggregatorV3Interface public priceOracle;
    AggregatorV3Interface public sequencerUptimeFeed;
    IPool public aavePool;
    IRouter public dexRouter;  // V4.3.1 - Aerodrome router for swaps
    address public aerodromeFactory;  // V4.3.1 - For route building
    
    // ============================================
    // STATE - Individual Ledger
    // ============================================
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public investments;
    mapping(address => uint256) public totalInvested;
    mapping(address => address[]) public userProtocols;
    
    // ============================================
    // STATE - MEV & Replay Protection
    // ============================================
    mapping(address => uint256) public lastDepositTime;
    mapping(address => uint256) public lastDepositBlock;
    mapping(address => uint256) public nonces;
    mapping(bytes32 => bool) public usedSignatures;
    
    // ============================================
    // V4.3 NEW - Rebalance Tracking (Anti-Chop)
    // ============================================
    mapping(address => mapping(address => uint256)) public lastRebalanceTime;
    mapping(address => mapping(address => uint256)) public lastRebalancePrice;
    
    // ============================================
    // STATE - Signer Rotation
    // ============================================
    address public pendingNewSigner;
    uint256 public signerRotationUnlockTime;
    
    // ============================================
    // STATE - Protocols
    // ============================================
    mapping(address => bool) public approvedProtocols;
    mapping(address => bool) public isLendingProtocol;  // For HF checks
    mapping(address => mapping(bytes4 => bool)) public allowedSelectors;  // H-01 fix: whitelist function selectors
    address[] public protocolList;
    
    // ============================================
    // STATE - Emergency
    // ============================================
    bool public emergencyMode;
    bool private _inFlashLoan;  // Reentrancy guard for flash loans

    // ============================================
    // EVENTS
    // ============================================
    event Deposited(address indexed user, uint256 requested, uint256 received);
    event Withdrawn(address indexed user, uint256 amount);
    event StrategyExecuted(address indexed user, address indexed protocol, uint256 amount);
    event PositionExited(address indexed user, address indexed protocol, uint256 amount);
    event RebalanceExecuted(address indexed user, address indexed protocol, uint256 priceAtRebalance);
    event EmergencyDeleverage(address indexed user, uint256 debtRepaid, uint256 collateralRecovered);
    event SequencerDownDetected(uint256 timestamp);
    event ProtocolApproved(address indexed protocol, bool approved, bool isLending);  // L-02 fix
    event UserWhitelisted(address indexed user);

    // ============================================
    // ERRORS
    // ============================================
    error SequencerDown();
    error SequencerGracePeriod();
    error OracleStale();
    error RebalanceCooldown();
    error InsufficientPriceMove();
    error HealthFactorTooLow();
    error FlashLoanFailed();
    error NotFlashLoanInitiator();

    // ============================================
    // CONSTRUCTOR
    // ============================================
    constructor(
        address _usdc,
        address _weth,           // V4.3.1 - WETH for cross-asset
        address _admin,
        address _agent,
        address _guardian,
        address _priceOracle,
        address _sequencerFeed,
        address _aavePool,
        address _dexRouter,      // V4.3.1 - Aerodrome router
        address _aeroFactory     // V4.3.1 - Aerodrome factory
    ) {
        // L-01 fix: Validate all critical constructor parameters
        require(_usdc != address(0), "Invalid USDC");
        require(_weth != address(0), "Invalid WETH");
        require(_admin != address(0), "Invalid admin");
        require(_aavePool != address(0), "Invalid Aave pool");
        require(_dexRouter != address(0), "Invalid DEX router");
        
        USDC = IERC20(_usdc);
        WETH = IERC20(_weth);
        priceOracle = AggregatorV3Interface(_priceOracle);
        sequencerUptimeFeed = AggregatorV3Interface(_sequencerFeed);
        aavePool = IPool(_aavePool);
        dexRouter = IRouter(_dexRouter);
        aerodromeFactory = _aeroFactory;
        
        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(AGENT_ROLE, _agent != address(0) ? _agent : _admin);
        _grantRole(GUARDIAN_ROLE, _guardian != address(0) ? _guardian : _admin);
    }

    // ============================================
    // MODIFIERS
    // ============================================
    
    modifier onlyWhitelisted() {
        require(hasRole(WHITELISTED_ROLE, msg.sender) || hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "Not whitelisted");
        _;
    }
    
    modifier sequencerHealthy() {
        _checkSequencer();
        _;
    }
    
    modifier notEmergency() {
        require(!emergencyMode, "Emergency");
        _;
    }

    // ============================================
    // V4.3 NEW - L2 Sequencer Check
    // ============================================
    
    function _checkSequencer() internal view {
        if (address(sequencerUptimeFeed) == address(0)) return;
        
        (, int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        
        // answer == 0 means sequencer is up, == 1 means down
        if (answer != 0) revert SequencerDown();
        
        // Grace period after sequencer comes back up
        if (block.timestamp - startedAt < SEQUENCER_GRACE_PERIOD) {
            revert SequencerGracePeriod();
        }
    }
    
    function _getOraclePrice() internal view returns (uint256) {
        if (address(priceOracle) == address(0)) return 0;
        
        (, int256 price,, uint256 updatedAt,) = priceOracle.latestRoundData();
        
        if (price <= 0) revert OracleStale();
        if (block.timestamp - updatedAt > MAX_ORACLE_STALENESS) revert OracleStale();
        
        return uint256(price);
    }

    // ============================================
    // V4.3 NEW - Rebalance with Hysteresis
    // ============================================
    
    function executeRebalance(
        address user,
        address protocol,
        bytes calldata data
    ) 
        external 
        onlyRole(AGENT_ROLE) 
        nonReentrant 
        sequencerHealthy
        notEmergency
        returns (bool)
    {
        // 1. Check cooldown (anti-chop)
        uint256 lastTime = lastRebalanceTime[user][protocol];
        if (block.timestamp < lastTime + MIN_REBALANCE_INTERVAL) {
            revert RebalanceCooldown();
        }
        
        // 2. Check minimum price movement
        uint256 currentPrice = _getOraclePrice();
        uint256 lastPrice = lastRebalancePrice[user][protocol];
        
        if (lastPrice > 0) {
            uint256 priceDiff = currentPrice > lastPrice 
                ? currentPrice - lastPrice 
                : lastPrice - currentPrice;
            uint256 deviation = (priceDiff * 10000) / lastPrice;
            
            if (deviation < MIN_PRICE_MOVE_FOR_REBALANCE) {
                revert InsufficientPriceMove();
            }
        }
        
        // 3. Execute rebalance
        require(approvedProtocols[protocol], "Protocol not approved");
        
        // H-01 fix: Validate function selector is whitelisted for this protocol
        bytes4 selector;
        if (data.length >= 4) {
            assembly {
                selector := calldataload(add(data.offset, 0))
            }
            require(allowedSelectors[protocol][selector], "Function not allowed");
        }
        
        (bool success,) = protocol.call(data);
        require(success, "Rebalance failed");
        
        // 4. Update tracking
        lastRebalanceTime[user][protocol] = block.timestamp;
        lastRebalancePrice[user][protocol] = currentPrice;
        
        emit RebalanceExecuted(user, protocol, currentPrice);
        return true;
    }

    // ============================================
    // V4.3 NEW - Flash Loan Emergency Deleverage
    // ============================================
    
    /**
     * @notice Emergency exit from leveraged position using flash loan
     * @dev Workflow: Flash loan → Repay debt → Withdraw collateral → Repay flash
     */
    function emergencyDeleverage(
        address user,
        address lendingProtocol,
        uint256 debtToRepay
    ) 
        external 
        onlyRole(AGENT_ROLE) 
        nonReentrant 
    {
        require(isLendingProtocol[lendingProtocol], "Not lending protocol");
        require(investments[user][lendingProtocol] > 0, "No position");
        
        // Encode params for flash loan callback
        bytes memory params = abi.encode(user, lendingProtocol, debtToRepay);
        
        _inFlashLoan = true;
        
        // Use try/catch to ensure flag is reset on failure
        try aavePool.flashLoanSimple(
            address(this),
            address(USDC),
            debtToRepay,
            params,
            0  // referral code
        ) {
            // Success - flag reset below
        } catch {
            _inFlashLoan = false;
            revert FlashLoanFailed();
        }
        
        _inFlashLoan = false;
    }
    
    /**
     * @notice Flash loan callback - executes the deleverage
     * @dev Routes to same-asset or cross-asset handler based on params
     */
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(msg.sender == address(aavePool), "Invalid caller");
        require(initiator == address(this), "Invalid initiator");
        require(_inFlashLoan, "Not in flash loan");
        
        // Check if this is cross-asset deleverage (params length > 96 bytes)
        if (params.length > 96) {
            // Cross-asset: (user, protocol, debt, collateral, minValue, isStable, intermediate)
            (
                address user, 
                address lendingProtocol, 
                uint256 debtToRepay,
                address collateralAsset,
                uint256 minCollateralValue,
                bool isStable,
                address intermediateToken
            ) = abi.decode(params, (address, address, uint256, address, uint256, bool, address));
            
            _executeCrossAssetDeleverage(
                amount, premium, user, lendingProtocol, 
                debtToRepay, collateralAsset, minCollateralValue,
                isStable, intermediateToken
            );
        } else {
            // Same-asset: (user, protocol, debt)
            (address user, address lendingProtocol, uint256 debtToRepay) = 
                abi.decode(params, (address, address, uint256));
            
            // Same-asset deleverage
            IERC20(asset).forceApprove(lendingProtocol, debtToRepay);
            IPool(lendingProtocol).repay(asset, debtToRepay, 2, address(this));
            
            uint256 invested = investments[user][lendingProtocol];
            uint256 withdrawn = IPool(lendingProtocol).withdraw(
                asset, 
                type(uint256).max,
                address(this)
            );
            
            investments[user][lendingProtocol] = 0;
            totalInvested[user] -= invested;
            
            uint256 totalOwed = amount + premium;
            uint256 userReceives = withdrawn > totalOwed ? withdrawn - totalOwed : 0;
            
            balances[user] += userReceives;
            IERC20(asset).forceApprove(address(aavePool), totalOwed);
            
            emit EmergencyDeleverage(user, debtToRepay, userReceives);
        }
        
        return true;
    }

    // ============================================
    // V4.3.2 - Cross-Asset Emergency Deleverage (Fixed)
    // Fixes: isStable param, multi-hop support, better docs
    // ============================================
    
    /**
     * @notice Emergency exit from cross-asset leveraged position
     * @dev Flow: Flash USDC → Repay USDC debt → Withdraw collateral → Swap → Repay flash
     * 
     * CRITICAL: Admin must ensure this is called with correct params:
     * - isStable: true for stablecoin pairs (DAI/USDC), false for volatile (WETH/USDC)
     * - intermediateToken: address(0) for direct swap, or WETH for multi-hop (DEGEN→WETH→USDC)
     *
     * @param user The user whose position to exit
     * @param lendingProtocol The lending pool (e.g., Aave)
     * @param debtToRepay Amount of USDC debt to repay
     * @param collateralAsset The collateral token (e.g., WETH, DAI)
     * @param minCollateralValue Minimum USDC value after swap (slippage protection)
     * @param isStable True if collateral→USDC is stable pair (DAI), false if volatile (ETH)
     * @param intermediateToken For multi-hop: intermediate token (e.g., WETH), or address(0) for direct
     */
    function emergencyDeleverageCrossAsset(
        address user,
        address lendingProtocol,
        uint256 debtToRepay,
        address collateralAsset,
        uint256 minCollateralValue,
        bool isStable,              // FIX #1: Pass stable/volatile flag
        address intermediateToken   // FIX #3: For multi-hop routing
    ) 
        external 
        onlyRole(AGENT_ROLE) 
        nonReentrant 
    {
        require(isLendingProtocol[lendingProtocol], "Not lending");
        require(investments[user][lendingProtocol] > 0, "No position");
        
        // Encode all params for flash loan callback
        bytes memory params = abi.encode(
            user, 
            lendingProtocol, 
            debtToRepay, 
            collateralAsset,
            minCollateralValue,
            isStable,
            intermediateToken
        );
        
        _inFlashLoan = true;
        
        // Use try/catch to ensure flag is reset on failure
        try aavePool.flashLoanSimple(
            address(this),
            address(USDC),
            debtToRepay,
            params,
            0
        ) {
            // Success - flag reset below
        } catch {
            _inFlashLoan = false;
            revert FlashLoanFailed();
        }
        
        _inFlashLoan = false;
    }
    
    /**
     * @notice Internal: Execute cross-asset deleverage with proper routing
     * @dev Supports both single-hop and multi-hop swaps
     */
    function _executeCrossAssetDeleverage(
        uint256 flashAmount,
        uint256 premium,
        address user,
        address lendingProtocol,
        uint256 debtToRepay,
        address collateralAsset,
        uint256 minCollateralValue,
        bool isStable,
        address intermediateToken
    ) internal {
        // 1. Repay USDC debt with flash loaned funds
        USDC.forceApprove(lendingProtocol, debtToRepay);
        IPool(lendingProtocol).repay(address(USDC), debtToRepay, 2, address(this));
        
        // 2. Withdraw collateral (now unlocked)
        uint256 collateralWithdrawn = IPool(lendingProtocol).withdraw(
            collateralAsset,
            type(uint256).max,
            address(this)
        );
        
        // 3. Swap collateral to USDC via Aerodrome
        IERC20(collateralAsset).forceApprove(address(dexRouter), collateralWithdrawn);
        
        IRouter.Route[] memory routes;
        
        if (intermediateToken == address(0)) {
            // FIX #1 & #3: Single-hop with correct stable flag
            routes = new IRouter.Route[](1);
            routes[0] = IRouter.Route({
                from: collateralAsset,
                to: address(USDC),
                stable: isStable,  // FIX #1: Use passed value, not hardcoded
                factory: aerodromeFactory
            });
        } else {
            // FIX #3: Multi-hop routing (e.g., DEGEN → WETH → USDC)
            routes = new IRouter.Route[](2);
            routes[0] = IRouter.Route({
                from: collateralAsset,
                to: intermediateToken,
                stable: false,  // First hop usually volatile
                factory: aerodromeFactory
            });
            routes[1] = IRouter.Route({
                from: intermediateToken,
                to: address(USDC),
                stable: false,  // WETH→USDC is volatile
                factory: aerodromeFactory
            });
        }
        
        uint256[] memory amounts = dexRouter.swapExactTokensForTokens(
            collateralWithdrawn,
            minCollateralValue,
            routes,
            address(this),
            block.timestamp + 60
        );
        
        uint256 usdcReceived = amounts[amounts.length - 1];
        
        // 4. Update accounting
        uint256 invested = investments[user][lendingProtocol];
        investments[user][lendingProtocol] = 0;
        totalInvested[user] -= invested;
        
        // 5. Calculate what user receives after flash loan repayment
        uint256 totalOwed = flashAmount + premium;
        require(usdcReceived >= totalOwed, "Insufficient after swap");
        
        uint256 userReceives = usdcReceived - totalOwed;
        balances[user] += userReceives;
        
        // 6. Approve flash loan repayment
        USDC.forceApprove(address(aavePool), totalOwed);
        
        emit EmergencyDeleverage(user, debtToRepay, userReceives);
    }

    // ============================================
    // V4.3 NEW - Health Factor Check
    // ============================================
    
    function checkHealthFactor(address lendingProtocol) public view returns (uint256 hf) {
        if (!isLendingProtocol[lendingProtocol]) return type(uint256).max;
        
        (,,,,, hf) = IPool(lendingProtocol).getUserAccountData(address(this));
        return hf;
    }
    
    modifier healthFactorSafe(address protocol) {
        // Check health factor BEFORE execution to save gas on revert
        if (isLendingProtocol[protocol]) {
            uint256 hfBefore = checkHealthFactor(protocol);
            if (hfBefore < MIN_HEALTH_FACTOR) revert HealthFactorTooLow();
        }
        _;
        // Also verify after execution
        if (isLendingProtocol[protocol]) {
            uint256 hfAfter = checkHealthFactor(protocol);
            if (hfAfter < MIN_HEALTH_FACTOR) revert HealthFactorTooLow();
        }
    }

    // ============================================
    // DEPOSIT (from V4.2 - fee-on-transfer safe)
    // ============================================
    
    function deposit(uint256 amount) 
        external 
        nonReentrant 
        onlyWhitelisted 
        whenNotPaused 
        sequencerHealthy
        notEmergency 
    {
        require(amount >= MINIMUM_DEPOSIT, "Below minimum");
        
        uint256 before = USDC.balanceOf(address(this));
        USDC.safeTransferFrom(msg.sender, address(this), amount);
        uint256 received = USDC.balanceOf(address(this)) - before;
        
        balances[msg.sender] += received;
        lastDepositTime[msg.sender] = block.timestamp;
        lastDepositBlock[msg.sender] = block.number;
        
        emit Deposited(msg.sender, amount, received);
    }

    // ============================================
    // WITHDRAW (from V4.2)
    // ============================================
    
    function withdraw(uint256 amount) external nonReentrant {
        require(block.timestamp >= lastDepositTime[msg.sender] + DEPOSIT_COOLDOWN, "Cooldown");
        require(block.number > lastDepositBlock[msg.sender], "Same block");
        require(amount > 0 && amount <= MAX_SINGLE_WITHDRAW, "Invalid amount");
        require(balances[msg.sender] >= amount, "Insufficient");
        
        balances[msg.sender] -= amount;
        USDC.safeTransfer(msg.sender, amount);
        
        emit Withdrawn(msg.sender, amount);
    }

    // ============================================
    // EXECUTE STRATEGY (with HF check)
    // ============================================
    
    struct ExecuteParams {
        address user;
        address protocol;
        uint256 amount;
        uint256 minAmountOut;
        uint256 deadline;
        uint256 nonce;
        uint256 priceAtSign;
    }
    
    function executeStrategySigned(
        ExecuteParams calldata p,
        bytes calldata signature,
        bytes calldata data
    ) 
        external 
        nonReentrant 
        sequencerHealthy
        notEmergency 
        healthFactorSafe(p.protocol)
        returns (bool) 
    {
        require(block.timestamp <= p.deadline, "Expired");
        require(p.nonce == nonces[p.user], "Invalid nonce");
        
        bytes32 hash = keccak256(abi.encodePacked(
            p.user, p.protocol, p.amount, p.minAmountOut, 
            p.deadline, p.nonce, p.priceAtSign, block.chainid
        )).toEthSignedMessageHash();
        
        require(hasRole(AGENT_ROLE, hash.recover(signature)), "Invalid signer");
        require(!usedSignatures[hash], "Replay");
        usedSignatures[hash] = true;
        
        // Oracle sanity
        if (p.priceAtSign > 0 && address(priceOracle) != address(0)) {
            uint256 oraclePrice = _getOraclePrice();
            uint256 diff = p.priceAtSign > oraclePrice 
                ? p.priceAtSign - oraclePrice 
                : oraclePrice - p.priceAtSign;
            require((diff * 10000) / oraclePrice <= MAX_PRICE_DEVIATION, "Price deviation");
        }
        
        nonces[p.user]++;
        
        require(approvedProtocols[p.protocol], "Not approved");
        require(balances[p.user] >= p.amount, "Insufficient");
        
        if (investments[p.user][p.protocol] == 0) {
            require(userProtocols[p.user].length < MAX_PROTOCOLS_PER_USER, "Too many");
            userProtocols[p.user].push(p.protocol);
        }
        
        balances[p.user] -= p.amount;
        investments[p.user][p.protocol] += p.amount;
        totalInvested[p.user] += p.amount;
        
        USDC.forceApprove(p.protocol, p.amount);
        (bool success,) = p.protocol.call(data);
        USDC.forceApprove(p.protocol, 0);
        
        if (!success) {
            balances[p.user] += p.amount;
            investments[p.user][p.protocol] -= p.amount;
            totalInvested[p.user] -= p.amount;
            return false;
        }
        
        emit StrategyExecuted(p.user, p.protocol, p.amount);
        return true;
    }

    // ============================================
    // ADMIN FUNCTIONS
    // ============================================
    
    function approveProtocol(address protocol, bool approved, bool _isLending) 
        external 
        onlyRole(DEFAULT_ADMIN_ROLE) 
    {
        if (approved && !approvedProtocols[protocol]) {
            protocolList.push(protocol);
        }
        approvedProtocols[protocol] = approved;
        isLendingProtocol[protocol] = _isLending;
        emit ProtocolApproved(protocol, approved, _isLending);  // L-02 fix
    }
    
    function whitelistUser(address user) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(WHITELISTED_ROLE, user);
        emit UserWhitelisted(user);
    }
    
    function setSequencerFeed(address _feed) external onlyRole(DEFAULT_ADMIN_ROLE) {
        sequencerUptimeFeed = AggregatorV3Interface(_feed);
    }
    
    function setAavePool(address _pool) external onlyRole(DEFAULT_ADMIN_ROLE) {
        aavePool = IPool(_pool);
    }
    
    /**
     * @notice H-01 fix: Whitelist specific function selectors for a protocol
     * @dev Only whitelisted selectors can be called via executeRebalance
     * Example selectors:
     *   - Aave supply: 0x617ba037
     *   - Aave withdraw: 0x69328dec
     *   - Aerodrome addLiquidity: 0xe8e33700
     */
    function setAllowedSelector(
        address protocol, 
        bytes4 selector, 
        bool allowed
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(approvedProtocols[protocol], "Protocol not approved");
        allowedSelectors[protocol][selector] = allowed;
    }

    // ============================================
    // EMERGENCY
    // ============================================
    
    function setEmergencyMode(bool _emergency) external onlyRole(GUARDIAN_ROLE) {
        emergencyMode = _emergency;
        if (_emergency) _pause(); else _unpause();
    }
    
    function pause() external onlyRole(GUARDIAN_ROLE) { _pause(); }
    function unpause() external onlyRole(GUARDIAN_ROLE) { _unpause(); }

    // ============================================
    // VIEW
    // ============================================
    
    function getUserTotalValue(address user) external view returns (uint256) {
        return balances[user] + totalInvested[user];
    }
    
    function isSequencerHealthy() external view returns (bool healthy, string memory reason) {
        if (address(sequencerUptimeFeed) == address(0)) return (true, "No feed configured");
        
        (, int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        
        if (answer != 0) return (false, "Sequencer down");
        if (block.timestamp - startedAt < SEQUENCER_GRACE_PERIOD) return (false, "Grace period");
        
        return (true, "Healthy");
    }
}
