// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title TechneAgentWallet
 * @author Techne Protocol
 * @notice Autonomous yield wallet for Base chain - Single & Dual-sided strategies
 * @dev Supports:
 * - Single-sided: Lending pools (Aave, Morpho, Moonwell)
 * - Dual-sided: LP pools with auto-swap (Aerodrome)
 */

// Aerodrome Router interface
interface IAerodromeRouter {
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
    
    function addLiquidity(
        address tokenA,
        address tokenB,
        bool stable,
        uint256 amountADesired,
        uint256 amountBDesired,
        uint256 amountAMin,
        uint256 amountBMin,
        address to,
        uint256 deadline
    ) external returns (uint256 amountA, uint256 amountB, uint256 liquidity);
    
    function removeLiquidity(
        address tokenA,
        address tokenB,
        bool stable,
        uint256 liquidity,
        uint256 amountAMin,
        uint256 amountBMin,
        address to,
        uint256 deadline
    ) external returns (uint256 amountA, uint256 amountB);
    
    function getAmountsOut(
        uint256 amountIn,
        Route[] calldata routes
    ) external view returns (uint256[] memory amounts);
}

interface IAerodromeFactory {
    function getPool(address tokenA, address tokenB, bool stable) external view returns (address);
}

contract TechneAgentWallet is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ============================================
    // STRUCTS
    // ============================================
    struct UserDeposit {
        uint256 shares;
        uint256 depositTime;
    }

    struct LPPosition {
        address pool;
        address tokenA;
        address tokenB;
        bool stable;
        uint256 lpAmount;
    }

    // ============================================
    // STATE
    // ============================================
    
    // Base USDC
    IERC20 public immutable USDC;
    
    // Aerodrome Router on Base
    IAerodromeRouter public immutable router;
    address public immutable aerodromeFactory;
    
    // Total shares
    uint256 public totalShares;
    uint256 public totalDeposited;
    
    // User balances
    mapping(address => UserDeposit) public userDeposits;
    
    // LP positions
    LPPosition[] public lpPositions;
    
    // Agent address
    address public agent;
    
    // Settings
    uint256 public performanceFee = 1000; // 10%
    uint256 public constant MAX_FEE = 2000;
    uint256 public minDeposit = 10 * 1e6; // 10 USDC
    uint256 public defaultSlippage = 50; // 0.5%
    
    // Pool type: 0 = single-sided, 1 = dual-sided, 2 = all
    uint8 public poolType = 0;
    
    bool public emergencyMode = false;

    // ============================================
    // EVENTS
    // ============================================
    event Deposited(address indexed user, uint256 amount, uint256 shares);
    event TokenDeposited(address indexed user, address indexed token, uint256 amount, uint256 shares);
    event Withdrawn(address indexed user, uint256 amount, uint256 shares);
    event SwappedForLP(address indexed tokenIn, address indexed tokenOut, uint256 amountIn, uint256 amountOut);
    event LPDeposited(address indexed pool, uint256 amountA, uint256 amountB, uint256 lpTokens);
    event LPWithdrawn(address indexed pool, uint256 lpTokens, uint256 amountA, uint256 amountB);
    event PoolTypeChanged(uint8 oldType, uint8 newType);

    // ============================================
    // CONSTRUCTOR
    // ============================================
    constructor(
        address _usdc,
        address _router,
        address _factory,
        address _agent
    ) Ownable(msg.sender) {
        require(_usdc != address(0), "Invalid USDC");
        require(_router != address(0), "Invalid router");
        require(_agent != address(0), "Invalid agent");
        
        USDC = IERC20(_usdc);
        router = IAerodromeRouter(_router);
        aerodromeFactory = _factory;
        agent = _agent;
    }

    // ============================================
    // MODIFIERS
    // ============================================
    modifier onlyAgent() {
        require(msg.sender == agent || msg.sender == owner(), "Not authorized");
        _;
    }
    
    modifier notEmergency() {
        require(!emergencyMode, "Emergency mode active");
        _;
    }

    // ============================================
    // USER FUNCTIONS
    // ============================================
    
    function deposit(uint256 amount) external nonReentrant notEmergency {
        require(amount >= minDeposit, "Below minimum deposit");
        
        uint256 shares;
        if (totalShares == 0) {
            shares = amount;
        } else {
            shares = (amount * totalShares) / totalValue();
        }
        
        USDC.safeTransferFrom(msg.sender, address(this), amount);
        
        userDeposits[msg.sender].shares += shares;
        userDeposits[msg.sender].depositTime = block.timestamp;
        totalShares += shares;
        totalDeposited += amount;
        
        emit Deposited(msg.sender, amount, shares);
    }
    
    /**
     * @notice Deposit any supported token (USDC, WETH, etc.)
     * @param token Token address to deposit
     * @param amount Amount in token decimals
     */
    function depositToken(address token, uint256 amount) external nonReentrant notEmergency {
        require(amount > 0, "Zero amount");
        require(token != address(0), "Invalid token");
        
        // Transfer token in
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        
        // Calculate USD value for shares
        uint256 usdValue;
        if (token == address(USDC)) {
            usdValue = amount; // 1:1 for USDC
        } else {
            // For other tokens, use amount as-is for now
            // In production: use price oracle
            usdValue = amount;
        }
        
        // Calculate shares
        uint256 shares;
        if (totalShares == 0) {
            shares = usdValue;
        } else {
            shares = (usdValue * totalShares) / totalValue();
        }
        
        userDeposits[msg.sender].shares += shares;
        userDeposits[msg.sender].depositTime = block.timestamp;
        totalShares += shares;
        
        emit TokenDeposited(msg.sender, token, amount, shares);
    }
    
    function withdraw(uint256 shares) external nonReentrant {
        require(shares > 0, "Zero shares");
        require(userDeposits[msg.sender].shares >= shares, "Insufficient shares");
        
        uint256 amount = (shares * totalValue()) / totalShares;
        
        userDeposits[msg.sender].shares -= shares;
        totalShares -= shares;
        if (totalDeposited > amount) {
            totalDeposited -= amount;
        } else {
            totalDeposited = 0;
        }
        
        USDC.safeTransfer(msg.sender, amount);
        
        emit Withdrawn(msg.sender, amount, shares);
    }

    // ============================================
    // AGENT FUNCTIONS - LP Operations
    // ============================================
    
    /**
     * @notice Swap USDC for another token via Aerodrome
     * @param tokenOut Token to receive
     * @param amountIn Amount of USDC to swap
     * @param stable Whether to use stable pool
     */
    function swapUSDCFor(
        address tokenOut,
        uint256 amountIn,
        bool stable
    ) external onlyAgent notEmergency returns (uint256 amountOut) {
        require(amountIn > 0, "Zero amount");
        require(USDC.balanceOf(address(this)) >= amountIn, "Insufficient USDC");
        
        // Approve router
        USDC.forceApprove(address(router), amountIn);
        
        // Build route
        IAerodromeRouter.Route[] memory routes = new IAerodromeRouter.Route[](1);
        routes[0] = IAerodromeRouter.Route({
            from: address(USDC),
            to: tokenOut,
            stable: stable,
            factory: aerodromeFactory
        });
        
        // Get expected output
        uint256[] memory expectedAmounts = router.getAmountsOut(amountIn, routes);
        uint256 minOut = expectedAmounts[1] * (10000 - defaultSlippage) / 10000;
        
        // Execute swap
        uint256[] memory amounts = router.swapExactTokensForTokens(
            amountIn,
            minOut,
            routes,
            address(this),
            block.timestamp + 300
        );
        
        amountOut = amounts[amounts.length - 1];
        emit SwappedForLP(address(USDC), tokenOut, amountIn, amountOut);
    }
    
    /**
     * @notice Add liquidity to Aerodrome pool
     * @param tokenA First token (usually USDC)
     * @param tokenB Second token
     * @param amountA Amount of tokenA
     * @param amountB Amount of tokenB
     * @param stable Stable or volatile pool
     */
    function addLiquidityToPool(
        address tokenA,
        address tokenB,
        uint256 amountA,
        uint256 amountB,
        bool stable
    ) external onlyAgent notEmergency returns (uint256 lpTokens) {
        require(amountA > 0 && amountB > 0, "Zero amounts");
        
        // Approve tokens
        IERC20(tokenA).forceApprove(address(router), amountA);
        IERC20(tokenB).forceApprove(address(router), amountB);
        
        // Calculate minimums with slippage
        uint256 minA = amountA * (10000 - defaultSlippage) / 10000;
        uint256 minB = amountB * (10000 - defaultSlippage) / 10000;
        
        // Add liquidity
        (uint256 actualA, uint256 actualB, uint256 liquidity) = router.addLiquidity(
            tokenA,
            tokenB,
            stable,
            amountA,
            amountB,
            minA,
            minB,
            address(this),
            block.timestamp + 300
        );
        
        // Get pool address
        address pool = IAerodromeFactory(aerodromeFactory).getPool(tokenA, tokenB, stable);
        
        // Track position
        lpPositions.push(LPPosition({
            pool: pool,
            tokenA: tokenA,
            tokenB: tokenB,
            stable: stable,
            lpAmount: liquidity
        }));
        
        lpTokens = liquidity;
        emit LPDeposited(pool, actualA, actualB, liquidity);
    }
    
    /**
     * @notice Remove liquidity from a position
     * @param positionIndex Index in lpPositions array
     * @param lpAmount Amount of LP tokens to remove
     */
    function removeLiquidityFromPool(
        uint256 positionIndex,
        uint256 lpAmount
    ) external onlyAgent returns (uint256 amountA, uint256 amountB) {
        require(positionIndex < lpPositions.length, "Invalid position");
        LPPosition storage pos = lpPositions[positionIndex];
        require(lpAmount <= pos.lpAmount, "Exceeds position");
        
        // Approve LP tokens
        IERC20(pos.pool).forceApprove(address(router), lpAmount);
        
        // Remove liquidity
        (amountA, amountB) = router.removeLiquidity(
            pos.tokenA,
            pos.tokenB,
            pos.stable,
            lpAmount,
            0, // Accept any amount (emergency compatible)
            0,
            address(this),
            block.timestamp + 300
        );
        
        // Update position
        pos.lpAmount -= lpAmount;
        
        emit LPWithdrawn(pos.pool, lpAmount, amountA, amountB);
    }
    
    /**
     * @notice Full LP entry: swap half USDC and add liquidity
     * @param tokenB The token to pair with USDC
     * @param usdcAmount Total USDC to use
     * @param stable Use stable pool
     */
    function enterLPPosition(
        address tokenB,
        uint256 usdcAmount,
        bool stable
    ) external onlyAgent notEmergency returns (uint256 lpTokens) {
        require(usdcAmount >= minDeposit * 2, "Need at least 2x min deposit");
        require(poolType >= 1, "Dual-sided not enabled");
        
        uint256 halfUSDC = usdcAmount / 2;
        
        // Swap half USDC for tokenB
        uint256 tokenBAmount = _swapUSDCForToken(tokenB, halfUSDC, stable);
        
        emit SwappedForLP(address(USDC), tokenB, halfUSDC, tokenBAmount);
        
        // Add liquidity
        lpTokens = _addLiquidityInternal(tokenB, halfUSDC, tokenBAmount, stable);
    }
    
    function _swapUSDCForToken(address tokenOut, uint256 amountIn, bool stable) internal returns (uint256) {
        USDC.forceApprove(address(router), amountIn);
        
        IAerodromeRouter.Route[] memory routes = new IAerodromeRouter.Route[](1);
        routes[0] = IAerodromeRouter.Route({
            from: address(USDC),
            to: tokenOut,
            stable: stable,
            factory: aerodromeFactory
        });
        
        uint256[] memory amounts = router.swapExactTokensForTokens(
            amountIn,
            0, // Use 0 for simplicity, rely on pool price
            routes,
            address(this),
            block.timestamp + 300
        );
        
        return amounts[amounts.length - 1];
    }
    
    function _addLiquidityInternal(address tokenB, uint256 usdcAmt, uint256 tokenBAmt, bool stable) internal returns (uint256) {
        USDC.forceApprove(address(router), usdcAmt);
        IERC20(tokenB).forceApprove(address(router), tokenBAmt);
        
        (,, uint256 liquidity) = router.addLiquidity(
            address(USDC),
            tokenB,
            stable,
            usdcAmt,
            tokenBAmt,
            0,
            0,
            address(this),
            block.timestamp + 300
        );
        
        address pool = IAerodromeFactory(aerodromeFactory).getPool(address(USDC), tokenB, stable);
        
        lpPositions.push(LPPosition({
            pool: pool,
            tokenA: address(USDC),
            tokenB: tokenB,
            stable: stable,
            lpAmount: liquidity
        }));
        
        emit LPDeposited(pool, usdcAmt, tokenBAmt, liquidity);
        return liquidity;
    }

    // ============================================
    // VIEW FUNCTIONS
    // ============================================
    
    function totalValue() public view returns (uint256) {
        uint256 usdcBalance = USDC.balanceOf(address(this));
        // In production, would also calculate LP positions value
        return usdcBalance;
    }
    
    function getUserValue(address user) external view returns (uint256) {
        if (totalShares == 0) return 0;
        return (userDeposits[user].shares * totalValue()) / totalShares;
    }
    
    function getUserShares(address user) external view returns (uint256) {
        return userDeposits[user].shares;
    }
    
    function getLPPositionCount() external view returns (uint256) {
        return lpPositions.length;
    }

    // ============================================
    // ADMIN FUNCTIONS
    // ============================================
    
    function setAgent(address _agent) external onlyOwner {
        require(_agent != address(0), "Invalid agent");
        agent = _agent;
    }
    
    function setPoolType(uint8 _poolType) external onlyOwner {
        require(_poolType <= 2, "Invalid pool type");
        emit PoolTypeChanged(poolType, _poolType);
        poolType = _poolType;
    }
    
    function setSlippage(uint256 _slippage) external onlyOwner {
        require(_slippage <= 500, "Max 5% slippage");
        defaultSlippage = _slippage;
    }
    
    function setEmergencyMode(bool _emergency) external onlyOwner {
        emergencyMode = _emergency;
    }
    
    function emergencyWithdrawAll() external onlyOwner {
        require(emergencyMode, "Not in emergency mode");
        uint256 balance = USDC.balanceOf(address(this));
        USDC.safeTransfer(owner(), balance);
    }
}
