// Deploy TechneAgentWalletV2 - Institutional Grade
// Run: npx hardhat run scripts/deploy-v2.js --network base

const { ethers } = require("hardhat");

async function main() {
    console.log("🚀 Deploying TechneAgentWalletV2...\n");

    // Get deployer
    const [deployer] = await ethers.getSigners();
    console.log("Deployer:", deployer.address);

    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Balance:", ethers.formatEther(balance), "ETH\n");

    // ============================================
    // CONFIGURATION - Base Mainnet
    // ============================================

    // Base Mainnet addresses
    const config = {
        // Tokens
        USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",

        // Aerodrome (Base DEX)
        AERODROME_ROUTER: "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
        AERODROME_FACTORY: "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",

        // Chainlink USDC/USD Price Feed on Base
        USDC_PRICE_FEED: "0x7e860098F58bBFC8648a4311b374B1D669a2bc6B",

        // Agent address (backend executor)
        AGENT: deployer.address, // Change to dedicated agent wallet

        // Multi-sig signers (Team wallets)
        SIGNERS: [
            "0xa30a689ec0f9d717c5ba1098455b031b868b720f",  // Signer 1
            "0x58e66a7a6883ef761e6adb0f08b0d94f70343eb6",  // Signer 2
            "0x9cf94969639d0905a6cb617925f06052643cce04"   // Signer 3
        ]
    };

    console.log("📋 Configuration:");
    console.log("  USDC:", config.USDC);
    console.log("  Router:", config.AERODROME_ROUTER);
    console.log("  Price Feed:", config.USDC_PRICE_FEED);
    console.log("  Agent:", config.AGENT);
    console.log("  Signers:", config.SIGNERS.length, "addresses\n");

    // ============================================
    // DEPLOY
    // ============================================

    const TechneWallet = await ethers.getContractFactory("TechneAgentWalletV2");

    console.log("⏳ Deploying contract...");

    const wallet = await TechneWallet.deploy(
        config.USDC,
        config.AERODROME_ROUTER,
        config.AERODROME_FACTORY,
        config.AGENT,
        config.USDC_PRICE_FEED,
        config.SIGNERS
    );

    await wallet.waitForDeployment();

    const address = await wallet.getAddress();

    console.log("\n✅ TechneAgentWalletV2 deployed!");
    console.log("📍 Contract Address:", address);

    // ============================================
    // VERIFY ON BASESCAN
    // ============================================

    console.log("\n🔍 Verifying on Basescan...");

    try {
        await run("verify:verify", {
            address: address,
            constructorArguments: [
                config.USDC,
                config.AERODROME_ROUTER,
                config.AERODROME_FACTORY,
                config.AGENT,
                config.USDC_PRICE_FEED,
                config.SIGNERS
            ],
        });
        console.log("✅ Verified on Basescan!");
    } catch (e) {
        console.log("⚠️ Verification failed:", e.message);
        console.log("   You can verify manually later");
    }

    // ============================================
    // POST-DEPLOY SETUP
    // ============================================

    console.log("\n📝 Post-deployment setup:");

    // Approve common protocols
    const protocols = [
        { name: "Aerodrome", address: config.AERODROME_ROUTER },
        { name: "Morpho Blue", address: "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb" },
        { name: "Aave V3 Pool", address: "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5" },
        { name: "Moonwell", address: "0xfBb21d0380bEE3312B33c4353c8936a0F13EF26C" },
    ];

    for (const p of protocols) {
        try {
            const tx = await wallet.approveProtocol(p.address);
            await tx.wait();
            console.log(`  ✅ Approved: ${p.name}`);
        } catch (e) {
            console.log(`  ⚠️ Failed to approve ${p.name}:`, e.message);
        }
    }

    // Set pool type to allow all (single + dual)
    try {
        const tx = await wallet.setPoolType(2);
        await tx.wait();
        console.log("  ✅ Pool type set to: All (single + dual)");
    } catch (e) {
        console.log("  ⚠️ Failed to set pool type:", e.message);
    }

    // ============================================
    // OUTPUT SUMMARY
    // ============================================

    console.log("\n" + "=".repeat(60));
    console.log("🎉 DEPLOYMENT COMPLETE");
    console.log("=".repeat(60));
    console.log("\nContract Address:", address);
    console.log("\nNext steps:");
    console.log("1. Update frontend/agent-wallet-ui.js with new address");
    console.log("2. Update backend/.env with new address");
    console.log("3. Fund the agent wallet with ETH for gas");
    console.log("4. Test deposit flow");
    console.log("\nSecurity features enabled:");
    console.log("  ✅ 2-day timelock on agent changes");
    console.log("  ✅ Multi-sig (2/3) for large withdrawals");
    console.log("  ✅ Daily limit: $1,000,000");
    console.log("  ✅ Single TX limit: $100,000");
    console.log("  ✅ Circuit breaker (auto-pause on 3 failures)");
    console.log("  ✅ De-peg protection (USDC < $0.995 = pause)");
    console.log("  ✅ Protocol caps (25% max per protocol)");

    // Save deployment info
    const fs = require("fs");
    const deploymentInfo = {
        network: "base",
        contract: "TechneAgentWalletV2",
        address: address,
        deployer: deployer.address,
        timestamp: new Date().toISOString(),
        config: config
    };

    fs.writeFileSync(
        "deployments/base-v2.json",
        JSON.stringify(deploymentInfo, null, 2)
    );
    console.log("\n📁 Saved to: deployments/base-v2.json");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exit(1);
    });
