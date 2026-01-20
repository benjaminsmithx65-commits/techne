/**
 * Approve All Base Protocols on V4 Contract
 * Run: node scripts/approve-all-protocols.mjs
 */

import { createPublicClient, createWalletClient, http, parseAbi } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import 'dotenv/config';

const V4_ADDRESS = "0x360455d8c1bfee9d471d69026eed972997714903";

// All Base protocols to approve
const PROTOCOLS = {
    // Lending Protocols
    "AAVE_V3": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    "MORPHO_BLUE": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
    "COMPOUND_V3": "0x46e6b214b524310239732D51387075E0e70970bf",
    "MOONWELL": "0xfBb21d0380bEE3312B33c4353c8936a0F13EF26C",

    // Seamless Protocol
    "SEAMLESS_POOL": "0x8F44Fd754285aa6A2b8B9B97739B79746e0475a7",
    "SEAMLESS_USDC": "0x616a4E1db48e22028f6bbf20444Cd3b8e3273738",
    "SEAMLESS_WETH": "0x27d8c7273fd3fcc6956a0b370ce5fd4a7fc65c18",

    // Exactly Protocol
    "EXACTLY_USDC": "0x61EDAcB54aA8a689013682529df8914C87692E4b",
    "EXACTLY_WETH": "0x52eE5238e5676598551c8d2bBcCB62c72FC3A0c4",
    "EXACTLY_ROUTER": "0x85c21fA8AeE39891E115E2b28c3dB2dE5B0AaF4f",

    // Yield Aggregators
    "BEEFY_VAULT": "0x6d0176C5ea1e44b08D3dd001b0784cE42F47a3A7",  // Beefy Base vault router

    // Origin Protocol (OETH)
    "ORIGIN_OETH": "0x856c4Efb76C1D1AE02e20CEB03A2A6a08b0b8dC3",

    // Convex (if on Base)
    "CONVEX_BOOSTER": "0xF403C135812408BFbE8713b5A23a04b3D48AAE31",
};

const ABI = parseAbi([
    "function approveProtocol(address protocol, bool approved) external",
    "function approvedProtocols(address) view returns (bool)"
]);

async function main() {
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        console.error("❌ PRIVATE_KEY not set in .env");
        process.exit(1);
    }

    const account = privateKeyToAccount(`0x${privateKey.replace('0x', '')}`);
    console.log("🔧 Approving ALL protocols on TechneAgentWalletV4...");
    console.log("Admin:", account.address);
    console.log("Contract:", V4_ADDRESS);
    console.log("");

    const publicClient = createPublicClient({
        chain: base,
        transport: http("https://mainnet.base.org")
    });

    const walletClient = createWalletClient({
        account,
        chain: base,
        transport: http("https://mainnet.base.org")
    });

    let approved = 0;
    let skipped = 0;
    let failed = 0;

    for (const [name, addr] of Object.entries(PROTOCOLS)) {
        try {
            // Check if already approved
            const isApproved = await publicClient.readContract({
                address: V4_ADDRESS,
                abi: ABI,
                functionName: "approvedProtocols",
                args: [addr]
            });

            if (isApproved) {
                console.log(`✓ ${name}: Already approved`);
                skipped++;
                continue;
            }

            console.log(`⏳ Approving ${name}: ${addr.slice(0, 10)}...`);

            const tx = await walletClient.writeContract({
                address: V4_ADDRESS,
                abi: ABI,
                functionName: "approveProtocol",
                args: [addr, true]
            });

            const receipt = await publicClient.waitForTransactionReceipt({ hash: tx });
            console.log(`✅ ${name} approved! TX: ${tx.slice(0, 16)}...`);
            approved++;

            // Small delay between transactions
            await new Promise(r => setTimeout(r, 1000));

        } catch (e) {
            console.error(`❌ ${name} failed:`, e.message?.slice(0, 50));
            failed++;
        }
    }

    console.log("\n" + "=".repeat(50));
    console.log("📊 SUMMARY:");
    console.log(`  ✅ Approved: ${approved}`);
    console.log(`  ⏭️  Skipped (already approved): ${skipped}`);
    console.log(`  ❌ Failed: ${failed}`);
    console.log("=".repeat(50));
}

main().catch(console.error);
