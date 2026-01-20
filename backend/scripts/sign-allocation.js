#!/usr/bin/env node
/**
 * Sign allocation transaction for V4.3.3 TechneAgentWallet
 * Called by Python backend to generate correct signatures
 * 
 * Usage: node sign-allocation.js <user> <protocol> <amount> <deadline> <nonce> <private_key>
 * Output: JSON { messageHash, signature }
 */

const { keccak256, encodePacked, hexToBytes } = require('viem');
const { privateKeyToAccount } = require('viem/accounts');

async function main() {
    const args = process.argv.slice(2);

    if (args.length < 6) {
        console.error(JSON.stringify({ error: 'Usage: node sign-allocation.js <user> <protocol> <amount> <deadline> <nonce> <private_key>' }));
        process.exit(1);
    }

    const [user, protocol, amountStr, deadlineStr, nonceStr, privateKey] = args;

    const amount = BigInt(amountStr);
    const deadline = BigInt(deadlineStr);
    const nonce = BigInt(nonceStr);
    const minAmountOut = 0n;
    const priceAtSign = 0n;
    const chainId = 8453n;  // Base

    // Generate message hash matching Solidity's abi.encodePacked
    const packed = encodePacked(
        ['address', 'address', 'uint256', 'uint256', 'uint256', 'uint256', 'uint256', 'uint256'],
        [user, protocol, amount, minAmountOut, deadline, nonce, priceAtSign, chainId]
    );

    const messageHash = keccak256(packed);

    // Sign with EIP-191 prefix
    const pk = privateKey.startsWith('0x') ? privateKey : `0x${privateKey}`;
    const account = privateKeyToAccount(pk);

    const signature = await account.signMessage({
        message: { raw: hexToBytes(messageHash) }
    });

    // Output result as JSON
    console.log(JSON.stringify({
        messageHash,
        signature,
        signer: account.address,
        params: {
            user,
            protocol,
            amount: amount.toString(),
            minAmountOut: '0',
            deadline: deadline.toString(),
            nonce: nonce.toString(),
            priceAtSign: '0'
        }
    }));
}

main().catch(e => {
    console.error(JSON.stringify({ error: e.message }));
    process.exit(1);
});
