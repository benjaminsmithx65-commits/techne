const { ethers } = require("hardhat");

async function main() {
    console.log("=".repeat(60));
    console.log("DEPLOYING TechneAgentAccount V2 (with executeWithSessionKey)");
    console.log("=".repeat(60));

    const [deployer] = await ethers.getSigners();
    console.log("\nDeployer:", deployer.address);

    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Balance:", ethers.formatEther(balance), "ETH");

    // Deploy TechneAgentAccount implementation
    console.log("\n1. Deploying TechneAgentAccount implementation...");
    const TechneAgentAccount = await ethers.getContractFactory("TechneAgentAccount");
    const implementation = await TechneAgentAccount.deploy();
    await implementation.waitForDeployment();
    const implAddress = await implementation.getAddress();
    console.log("   Implementation deployed at:", implAddress);

    // Deploy TechneAgentFactory
    console.log("\n2. Deploying TechneAgentFactory...");

    // Session key address (derived from master secret)
    // For now, set to zero - will be configured later per-agent
    const defaultSessionKey = "0x0000000000000000000000000000000000000000";

    const TechneAgentFactory = await ethers.getContractFactory("TechneAgentFactory");
    const factory = await TechneAgentFactory.deploy(implAddress, defaultSessionKey);
    await factory.waitForDeployment();
    const factoryAddress = await factory.getAddress();
    console.log("   Factory deployed at:", factoryAddress);

    // Setup default protocols for Aerodrome + common DeFi
    console.log("\n3. Setting up default protocol whitelist...");

    // Aerodrome Router V2 on Base
    const AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43";
    // USDC on Base
    const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
    // WETH on Base
    const WETH = "0x4200000000000000000000000000000000000006";

    // Common ERC20 selectors
    const APPROVE_SELECTOR = "0x095ea7b3";  // approve(address,uint256)
    const TRANSFER_SELECTOR = "0xa9059cbb"; // transfer(address,uint256)

    // Aerodrome Router selectors
    const ADD_LIQUIDITY = "0xe8e33700";     // addLiquidity(...)
    const REMOVE_LIQUIDITY = "0xbaa2abde"; // removeLiquidity(...)
    const SWAP_EXACT_TOKENS = "0x38ed1739"; // swapExactTokensForTokens(...)

    const protocols = [
        USDC,
        WETH,
        AERODROME_ROUTER
    ];

    const selectors = [
        [APPROVE_SELECTOR, TRANSFER_SELECTOR],  // USDC
        [APPROVE_SELECTOR, TRANSFER_SELECTOR],  // WETH
        [ADD_LIQUIDITY, REMOVE_LIQUIDITY, SWAP_EXACT_TOKENS]  // Aerodrome
    ];

    const tx = await factory.setDefaultProtocols(protocols, selectors);
    await tx.wait();
    console.log("   Default protocols configured!");

    console.log("\n" + "=".repeat(60));
    console.log("DEPLOYMENT COMPLETE!");
    console.log("=".repeat(60));
    console.log("\nSave these addresses:");
    console.log("  IMPLEMENTATION:", implAddress);
    console.log("  FACTORY:", factoryAddress);
    console.log("\nUpdate .env with:");
    console.log(`  SMART_ACCOUNT_FACTORY_ADDRESS=${factoryAddress}`);
    console.log(`  SMART_ACCOUNT_IMPLEMENTATION_ADDRESS=${implAddress}`);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
