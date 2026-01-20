/**
 * Deploy TechneAgentWalletV43 (V4.3.2) to Base Mainnet
 * Features: Flash loan deleverage, cross-asset swaps, sequencer check
 * 
 * Run: npx hardhat run scripts/deploy-v43.js --network base
 */

import hre from "hardhat";
import fs from "fs";

// Base Mainnet Addresses
const ADDRESSES = {
    // Core Tokens
    USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    WETH: "0x4200000000000000000000000000000000000006",

    // Chainlink Oracles
    ETH_USD_ORACLE: "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",
    SEQUENCER_UPTIME: "0xBCF85224fc0756B9Fa45aA7892530B47e10b6433",

    // Aave V3 on Base
    AAVE_POOL: "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",

    // Aerodrome
    AERODROME_ROUTER: "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
    AERODROME_FACTORY: "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
};

async function main() {
    const [deployer] = await hre.ethers.getSigners();

    console.log("🚀 Deploying TechneAgentWalletV43 to Base Mainnet");
    console.log("================================================");
    console.log("Deployer:", deployer.address);

    const balance = await hre.ethers.provider.getBalance(deployer.address);
    console.log("Balance:", hre.ethers.formatEther(balance), "ETH");
    console.log("");

    // Get contract factory
    const V43Factory = await hre.ethers.getContractFactory("TechneAgentWalletV43");

    console.log("📋 Constructor Parameters:");
    console.log("  USDC:", ADDRESSES.USDC);
    console.log("  WETH:", ADDRESSES.WETH);
    console.log("  Admin:", deployer.address);
    console.log("  Agent:", deployer.address);
    console.log("  Guardian:", deployer.address);
    console.log("  Price Oracle:", ADDRESSES.ETH_USD_ORACLE);
    console.log("  Sequencer Feed:", ADDRESSES.SEQUENCER_UPTIME);
    console.log("  Aave Pool:", ADDRESSES.AAVE_POOL);
    console.log("  DEX Router:", ADDRESSES.AERODROME_ROUTER);
    console.log("  DEX Factory:", ADDRESSES.AERODROME_FACTORY);
    console.log("");

    console.log("⏳ Deploying...");

    const contract = await V43Factory.deploy(
        ADDRESSES.USDC,
        ADDRESSES.WETH,
        deployer.address,  // admin
        deployer.address,  // agent
        deployer.address,  // guardian
        ADDRESSES.ETH_USD_ORACLE,
        ADDRESSES.SEQUENCER_UPTIME,
        ADDRESSES.AAVE_POOL,
        ADDRESSES.AERODROME_ROUTER,
        ADDRESSES.AERODROME_FACTORY
    );

    await contract.waitForDeployment();
    const contractAddress = await contract.getAddress();

    console.log("");
    console.log("✅ TechneAgentWalletV43 Deployed!");
    console.log("================================");
    console.log("📍 Contract Address:", contractAddress);
    console.log("");

    // Save deployment info
    const deployment = {
        version: "V4.3.2",
        address: contractAddress,
        deployer: deployer.address,
        network: "base",
        chainId: 8453,
        timestamp: new Date().toISOString(),
        constructor: {
            usdc: ADDRESSES.USDC,
            weth: ADDRESSES.WETH,
            admin: deployer.address,
            agent: deployer.address,
            guardian: deployer.address,
            priceOracle: ADDRESSES.ETH_USD_ORACLE,
            sequencerFeed: ADDRESSES.SEQUENCER_UPTIME,
            aavePool: ADDRESSES.AAVE_POOL,
            dexRouter: ADDRESSES.AERODROME_ROUTER,
            dexFactory: ADDRESSES.AERODROME_FACTORY
        },
        features: [
            "Flash Loan Deleverage",
            "Cross-Asset Swap (multi-hop)",
            "L2 Sequencer Check",
            "Health Factor Monitoring",
            "Rebalance Hysteresis (4h cooldown)",
            "Fee-on-Transfer Safe",
            "Signature Replay Protection"
        ]
    };

    fs.writeFileSync(
        "deployments/v43-base-mainnet.json",
        JSON.stringify(deployment, null, 2)
    );

    console.log("📁 Deployment saved to deployments/v43-base-mainnet.json");
    console.log("");
    console.log("🔧 Next steps:");
    console.log("  1. Verify on Basescan");
    console.log("  2. Whitelist users");
    console.log("  3. Approve protocols (Aave, Moonwell, etc.)");
    console.log("  4. Transfer AGENT_ROLE to backend signer");
    console.log("  5. Transfer DEFAULT_ADMIN_ROLE to Gnosis Safe");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exit(1);
    });
