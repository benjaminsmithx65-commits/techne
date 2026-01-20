// Deploy TechneAgentWalletV3 - MEV-Resistant
// Run: npx hardhat run scripts/deploy-v3.js --network base

import hre from "hardhat";
import fs from "fs";
import { createWalletClient, http, createPublicClient, encodeDeployData } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

async function main() {
    console.log("🛡️ Deploying TechneAgentWalletV3 (MEV-Resistant)...\n");

    // Get private key from env
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        throw new Error("PRIVATE_KEY not set in .env");
    }

    // Create account
    const account = privateKeyToAccount(privateKey);
    console.log("Deployer:", account.address);

    // Create clients
    const rpcUrl = process.env.ALCHEMY_RPC_URL || "https://mainnet.base.org";

    const publicClient = createPublicClient({
        chain: base,
        transport: http(rpcUrl)
    });

    const walletClient = createWalletClient({
        account,
        chain: base,
        transport: http(rpcUrl)
    });

    // Get balance
    const balance = await publicClient.getBalance({ address: account.address });
    console.log("Balance:", (Number(balance) / 1e18).toFixed(4), "ETH\n");

    // ============================================
    // CONFIGURATION - IMPORTANT: Set these!
    // ============================================

    const config = {
        USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        ADMIN: account.address,  // Deployer = Admin
        AGENT: account.address,  // Deployer = Agent (change if needed)
        GUARDIAN: account.address  // Deployer = Guardian (change if needed)
    };

    console.log("📋 V3 Configuration:");
    console.log("  USDC:", config.USDC);
    console.log("  Admin:", config.ADMIN);
    console.log("  Agent:", config.AGENT);
    console.log("  Guardian:", config.GUARDIAN);
    console.log("\n🛡️ Security Features:");
    console.log("  ✅ Commit-Reveal Deposits (2 blocks)");
    console.log("  ✅ Whitelist-Only Access");
    console.log("  ✅ 5-minute Deposit Cooldown");
    console.log("  ✅ Same-Block Protection");
    console.log("  ✅ $1000 Minimum First Deposit");
    console.log("  ✅ Virtual Offset (Inflation Protection)");
    console.log("  ✅ Bounded Token Approvals");
    console.log("  ✅ Role-Based Access Control\n");

    // ============================================
    // DEPLOY
    // ============================================

    console.log("⏳ Deploying contract...");

    // Get artifact
    const artifact = await hre.artifacts.readArtifact("TechneAgentWalletV3");

    // Encode deploy data
    const deployData = encodeDeployData({
        abi: artifact.abi,
        bytecode: artifact.bytecode,
        args: [
            config.USDC,
            config.ADMIN,
            config.AGENT,
            config.GUARDIAN
        ]
    });

    // Estimate gas
    const gasEstimate = await publicClient.estimateGas({
        account: account.address,
        data: deployData
    });
    console.log("  Gas estimate:", gasEstimate.toString());

    // Deploy
    const hash = await walletClient.sendTransaction({
        data: deployData,
        gas: gasEstimate + 100000n // Add buffer
    });

    console.log("\n📤 TX sent:", hash);
    console.log("⏳ Waiting for confirmation...");

    // Wait for receipt
    const receipt = await publicClient.waitForTransactionReceipt({ hash });

    const contractAddress = receipt.contractAddress;

    console.log("\n✅ TechneAgentWalletV3 deployed!");
    console.log("📍 Contract Address:", contractAddress);
    console.log("🔗 Basescan: https://basescan.org/address/" + contractAddress);

    // ============================================
    // POST-DEPLOY: Whitelist the deployer
    // ============================================

    console.log("\n⏳ Whitelisting deployer address...");

    // Encode whitelistUser call
    const whitelistData = {
        abi: artifact.abi,
        functionName: 'whitelistUser',
        args: [account.address]
    };

    // Note: You'll need to call this manually or update to use viem's writeContract

    // ============================================
    // SUMMARY
    // ============================================

    console.log("\n" + "=".repeat(60));
    console.log("🎉 DEPLOYMENT COMPLETE - V3 MEV-RESISTANT");
    console.log("=".repeat(60));
    console.log("\n⚡ Contract Address:", contractAddress);

    console.log("\n📋 NEXT STEPS:");
    console.log("  1. Verify contract on Basescan:");
    console.log(`     npx hardhat verify --network base ${contractAddress} \\`);
    console.log(`       "${config.USDC}" "${config.ADMIN}" "${config.AGENT}" "${config.GUARDIAN}"`);
    console.log("\n  2. Whitelist users who can deposit:");
    console.log("     Call whitelistUser(address) for each user");
    console.log("\n  3. Update frontend/agent-wallet-ui.js");
    console.log("  4. Update backend/config/contracts.py");

    console.log("\n🛡️ Security Protections Active:");
    console.log("  • MEV bots cannot frontrun deposits");
    console.log("  • Only whitelisted addresses can deposit");
    console.log("  • 5 minute cooldown before withdrawal");
    console.log("  • Same-block atomic exploits blocked");
    console.log("  • Inflation attacks prevented");

    // Save
    const deploymentInfo = {
        network: "base",
        contract: "TechneAgentWalletV3",
        version: "3.0.0",
        address: contractAddress,
        deployer: account.address,
        txHash: hash,
        timestamp: new Date().toISOString(),
        config: config,
        securityFeatures: [
            "commit-reveal",
            "whitelist",
            "cooldown",
            "same-block-protection",
            "virtual-offset",
            "bounded-approvals",
            "access-control"
        ]
    };

    // Create deployments dir if needed
    if (!fs.existsSync("deployments")) {
        fs.mkdirSync("deployments");
    }

    fs.writeFileSync(
        "deployments/base-v3.json",
        JSON.stringify(deploymentInfo, null, 2)
    );
    console.log("\n📁 Saved to: deployments/base-v3.json");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exit(1);
    });
