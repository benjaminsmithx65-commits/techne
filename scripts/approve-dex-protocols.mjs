/**
 * Approve DEX Protocols (Aerodrome, Curve, Uniswap, Merkl)
 * Run: node scripts/approve-dex-protocols.mjs
 */

import { createPublicClient, createWalletClient, http, parseAbi } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import 'dotenv/config';

const V4_ADDRESS = "0x360455d8c1bfee9d471d69026eed972997714903";

// DEX & AMM protocols on Base
const PROTOCOLS = {
    "AERODROME_ROUTER": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
    "UNISWAP_V3_ROUTER": "0x6fF5693b99212Da76ad316178A184AB56D299b43",
    "CURVE_4POOL": "0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f",
    "CURVE_CBETH_WETH": "0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59",
    "CURVE_TRICRYPTO": "0x6e53187c1ADF84c8fA72207a33f92fc6FBD9e0c5",
    "MERKL_DISTRIBUTOR": "0x3Ef3D8bA38EBe18DB133cEc108f4D14CE00Dd9Ae",
    "EXTRA_FINANCE": "0x3194cBDC3dbcd3E11a07892e7bA5c3394048Cc87",  // Extra Finance on Base
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
    console.log("🔧 Approving DEX/AMM protocols on TechneAgentWalletV4...\n");

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

    for (const [name, addr] of Object.entries(PROTOCOLS)) {
        try {
            const isApproved = await publicClient.readContract({
                address: V4_ADDRESS,
                abi: ABI,
                functionName: "approvedProtocols",
                args: [addr]
            });

            if (isApproved) {
                console.log(`✓ ${name}: Already approved`);
                continue;
            }

            console.log(`⏳ Approving ${name}...`);

            const tx = await walletClient.writeContract({
                address: V4_ADDRESS,
                abi: ABI,
                functionName: "approveProtocol",
                args: [addr, true]
            });

            await publicClient.waitForTransactionReceipt({ hash: tx });
            console.log(`✅ ${name} approved!`);
            approved++;

            await new Promise(r => setTimeout(r, 1000));
        } catch (e) {
            console.error(`❌ ${name} failed:`, e.message?.slice(0, 60));
        }
    }

    console.log(`\n✅ Done! ${approved} new protocols approved.`);
}

main().catch(console.error);
