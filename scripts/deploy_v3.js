// SPDX-License-Identifier: MIT
// Deploy script for TechneAgentAccount V3 + TechneAgentFactory V3

const { ethers } = require("hardhat");

async function main() {
    console.log("=== Techne Smart Account V3 Deployment ===\n");

    const [deployer] = await ethers.getSigners();
    console.log("Deployer:", deployer.address);

    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Balance:", ethers.formatEther(balance), "ETH\n");

    // Backend session key address (from PRIVATE_KEY in .env)
    const BACKEND_SESSION_KEY = "0xa30A689ec0F9D717C5bA1098455B031b868B720f";

    // =============== STEP 1: Deploy Implementation ===============
    console.log("1. Deploying TechneAgentAccount implementation...");

    const TechneAgentAccount = await ethers.getContractFactory("TechneAgentAccount");
    const implementation = await TechneAgentAccount.deploy();
    await implementation.waitForDeployment();

    const implAddress = await implementation.getAddress();
    console.log("   ✅ Implementation deployed:", implAddress);

    // =============== STEP 2: Deploy Factory ===============
    console.log("\n2. Deploying TechneAgentFactory V3...");

    const TechneAgentFactory = await ethers.getContractFactory("TechneAgentFactory");
    const factory = await TechneAgentFactory.deploy(implAddress, BACKEND_SESSION_KEY);
    await factory.waitForDeployment();

    const factoryAddress = await factory.getAddress();
    console.log("   ✅ Factory deployed:", factoryAddress);

    // =============== STEP 3: Configure Default Whitelists ===============
    console.log("\n3. Configuring default protocol whitelists...");

    // Aerodrome Router V2
    const AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43";
    // USDC on Base
    const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
    // WETH on Base
    const WETH = "0x4200000000000000000000000000000000000006";
    // Aave Pool V3
    const AAVE_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5";

    // Common selectors
    const SELECTORS = {
        // ERC20
        approve: "0x095ea7b3",
        transfer: "0xa9059cbb",
        // Aerodrome
        swapExactTokensForTokens: "0x38ed1739",
        addLiquidity: "0xe8e33700",
        removeLiquidity: "0xbaa2abde",
        // Aave
        supply: "0x617ba037",
        withdraw: "0x69328dec",
    };

    const protocols = [USDC, WETH, AERODROME_ROUTER, AAVE_POOL];
    const selectors = [
        [SELECTORS.approve, SELECTORS.transfer], // USDC
        [SELECTORS.approve, SELECTORS.transfer], // WETH
        [SELECTORS.swapExactTokensForTokens, SELECTORS.addLiquidity, SELECTORS.removeLiquidity], // Aerodrome
        [SELECTORS.supply, SELECTORS.withdraw], // Aave
    ];

    const tx = await factory.setDefaultProtocols(protocols, selectors);
    await tx.wait();
    console.log("   ✅ Default protocols configured");

    // =============== SUMMARY ===============
    console.log("\n========================================");
    console.log("           DEPLOYMENT COMPLETE          ");
    console.log("========================================");
    console.log("\nAddresses to update in backend:");
    console.log(`  IMPLEMENTATION: ${implAddress}`);
    console.log(`  FACTORY_V3:     ${factoryAddress}`);
    console.log(`  SESSION_KEY:    ${BACKEND_SESSION_KEY}`);
    console.log(`  DAILY_LIMIT:    $1,000,000 USD`);
    console.log("\nUpdate these files:");
    console.log("  - backend/services/smart_account_service.py");
    console.log("  - backend/api/agent_wallet_router.py");
    console.log("  - frontend/agent-wallet-ui.js");
    console.log("========================================\n");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
