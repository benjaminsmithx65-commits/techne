// Deploy TechneAgentWalletV4 - Individual Model
// Run: npx hardhat run scripts/deploy-v4.js --network base

import 'dotenv/config';
import hre from "hardhat";
import fs from "fs";
import { createWalletClient, http, createPublicClient, encodeDeployData } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

async function main() {
    console.log("🚀 Deploying TechneAgentWalletV4 (Individual Model)...\n");

    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        throw new Error("PRIVATE_KEY not set in .env");
    }

    const account = privateKeyToAccount(privateKey);
    console.log("Deployer:", account.address);

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

    const balance = await publicClient.getBalance({ address: account.address });
    console.log("Balance:", (Number(balance) / 1e18).toFixed(4), "ETH\n");

    // ============================================
    // CONFIGURATION
    // ============================================

    const config = {
        USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        ADMIN: account.address,
        AGENT: process.env.AGENT_ADDRESS || account.address,
        GUARDIAN: account.address
    };

    console.log("📋 V4 Configuration (Individual Model):");
    console.log("  USDC:", config.USDC);
    console.log("  Admin:", config.ADMIN);
    console.log("  Agent:", config.AGENT);
    console.log("  Guardian:", config.GUARDIAN);
    console.log("\n🎯 V4 Features:");
    console.log("  ✅ Per-user balance tracking (no shares!)");
    console.log("  ✅ Per-user investment tracking (user->protocol->amount)");
    console.log("  ✅ Individual withdraw (only YOUR funds)");
    console.log("  ✅ Protocol whitelist");
    console.log("  ✅ MEV protection (cooldown, same-block)");
    console.log("");

    // ============================================
    // DEPLOY
    // ============================================

    console.log("⏳ Deploying contract...");

    const artifact = await hre.artifacts.readArtifact("TechneAgentWalletV4");

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

    const gasEstimate = await publicClient.estimateGas({
        account: account.address,
        data: deployData
    });
    console.log("  Gas estimate:", gasEstimate.toString());

    const hash = await walletClient.sendTransaction({
        data: deployData,
        gas: gasEstimate + 100000n
    });

    console.log("\n📤 TX sent:", hash);
    console.log("⏳ Waiting for confirmation...");

    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    const contractAddress = receipt.contractAddress;

    console.log("\n✅ TechneAgentWalletV4 deployed!");
    console.log("📍 Contract Address:", contractAddress);
    console.log("🔗 Basescan: https://basescan.org/address/" + contractAddress);

    // ============================================
    // SAVE
    // ============================================

    const deploymentInfo = {
        network: "base",
        contract: "TechneAgentWalletV4",
        version: "4.0.0",
        model: "individual",
        address: contractAddress,
        deployer: account.address,
        txHash: hash,
        timestamp: new Date().toISOString(),
        config: config,
        features: [
            "per-user-balance",
            "per-user-investments",
            "individual-withdraw",
            "protocol-whitelist",
            "mev-protection"
        ]
    };

    if (!fs.existsSync("deployments")) {
        fs.mkdirSync("deployments");
    }

    fs.writeFileSync(
        "deployments/base-v4.json",
        JSON.stringify(deploymentInfo, null, 2)
    );

    console.log("\n📁 Saved to: deployments/base-v4.json");
    console.log("\n" + "=".repeat(60));
    console.log("🎉 V4 INDIVIDUAL MODEL DEPLOYED!");
    console.log("=".repeat(60));
    console.log("\n📋 NEXT STEPS:");
    console.log("  1. Whitelist users: whitelistUser(address)");
    console.log("  2. Approve protocols: approveProtocol(protocol, true)");
    console.log("  3. Update frontend contract address");
    console.log("  4. Users can deposit individually!");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exit(1);
    });
