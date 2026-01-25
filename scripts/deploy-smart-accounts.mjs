/**
 * Deploy TechneAgentAccount + TechneAgentFactory to Base
 * 
 * Run: node scripts/deploy-smart-accounts.mjs
 */

import { createWalletClient, createPublicClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base, baseSepolia } from 'viem/chains';
import fs from 'fs';
import 'dotenv/config';

// Base Mainnet Protocol Addresses
const PROTOCOLS = {
    // Lending
    AAVE_POOL: "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    MOONWELL_COMPTROLLER: "0xfBb21d0380beE3312B33c4353c8936a0F13EF26C",
    // DEX
    AERODROME_ROUTER: "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
    // Tokens
    USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    WETH: "0x4200000000000000000000000000000000000006",
};

// Common function selectors to whitelist
const SELECTORS = {
    // Aave
    supply: "0x617ba037",
    withdraw: "0x69328dec",
    borrow: "0xa415bcad",
    repay: "0x573ade81",
    // Aerodrome
    swapExactTokensForTokens: "0xcac88ea9",
    addLiquidity: "0x5a47ddc3",
    removeLiquidity: "0x0dede6c4",
    // ERC20
    approve: "0x095ea7b3",
    transfer: "0xa9059cbb",
};

async function main() {
    // Select network
    const useTestnet = process.argv.includes('--testnet');
    const chain = useTestnet ? baseSepolia : base;
    const rpcUrl = useTestnet
        ? "https://sepolia.base.org"
        : process.env.ALCHEMY_RPC_URL || "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb";

    console.log(`🚀 Deploying Smart Account System to ${chain.name}`);
    console.log("=".repeat(60));

    // Setup clients
    const pk = process.env.PRIVATE_KEY.startsWith('0x')
        ? process.env.PRIVATE_KEY
        : `0x${process.env.PRIVATE_KEY}`;
    const account = privateKeyToAccount(pk);

    const publicClient = createPublicClient({
        chain,
        transport: http(rpcUrl)
    });

    const walletClient = createWalletClient({
        account,
        chain,
        transport: http(rpcUrl)
    });

    console.log("Deployer:", account.address);
    const balance = await publicClient.getBalance({ address: account.address });
    console.log("Balance:", Number(balance) / 1e18, "ETH");
    console.log();

    // Load artifacts
    const accountArtifact = JSON.parse(
        fs.readFileSync('./artifacts/contracts/TechneAgentAccount.sol/TechneAgentAccount.json', 'utf8')
    );
    const factoryArtifact = JSON.parse(
        fs.readFileSync('./artifacts/contracts/TechneAgentFactory.sol/TechneAgentFactory.json', 'utf8')
    );

    // Step 1: Deploy Implementation (TechneAgentAccount)
    console.log("📦 Step 1: Deploying TechneAgentAccount implementation...");

    const { encodeDeployData } = await import('viem');

    const accountDeployData = encodeDeployData({
        abi: accountArtifact.abi,
        bytecode: accountArtifact.bytecode,
        args: []
    });

    const accountHash = await walletClient.sendTransaction({
        data: accountDeployData,
    });
    console.log("   TX:", accountHash);

    const accountReceipt = await publicClient.waitForTransactionReceipt({ hash: accountHash });
    const implementationAddress = accountReceipt.contractAddress;
    console.log("   ✅ Implementation:", implementationAddress);
    console.log();

    // Step 2: Deploy Factory
    console.log("🏭 Step 2: Deploying TechneAgentFactory...");

    const factoryDeployData = encodeDeployData({
        abi: factoryArtifact.abi,
        bytecode: factoryArtifact.bytecode,
        args: [
            implementationAddress,  // implementation
            account.address         // defaultSessionKey (deployer for now)
        ]
    });

    const factoryHash = await walletClient.sendTransaction({
        data: factoryDeployData,
    });
    console.log("   TX:", factoryHash);

    const factoryReceipt = await publicClient.waitForTransactionReceipt({ hash: factoryHash });
    const factoryAddress = factoryReceipt.contractAddress;
    console.log("   ✅ Factory:", factoryAddress);
    console.log();

    // Step 3: Configure default protocols
    console.log("⚙️ Step 3: Configuring default protocols...");

    const factory = {
        address: factoryAddress,
        abi: factoryArtifact.abi
    };

    const defaultProtocols = [
        PROTOCOLS.AAVE_POOL,
        PROTOCOLS.AERODROME_ROUTER,
        PROTOCOLS.USDC,
        PROTOCOLS.WETH
    ];

    const defaultSelectors = [
        // Aave
        [SELECTORS.supply, SELECTORS.withdraw, SELECTORS.borrow, SELECTORS.repay],
        // Aerodrome
        [SELECTORS.swapExactTokensForTokens, SELECTORS.addLiquidity, SELECTORS.removeLiquidity],
        // USDC
        [SELECTORS.approve, SELECTORS.transfer],
        // WETH
        [SELECTORS.approve, SELECTORS.transfer]
    ];

    const { encodeFunctionData } = await import('viem');

    const configData = encodeFunctionData({
        abi: factoryArtifact.abi,
        functionName: 'setDefaultProtocols',
        args: [defaultProtocols, defaultSelectors]
    });

    const configHash = await walletClient.sendTransaction({
        to: factoryAddress,
        data: configData,
    });
    console.log("   TX:", configHash);
    await publicClient.waitForTransactionReceipt({ hash: configHash });
    console.log("   ✅ Default protocols configured");
    console.log();

    // Save deployment info
    const deployment = {
        network: chain.name,
        chainId: chain.id,
        timestamp: new Date().toISOString(),
        deployer: account.address,
        contracts: {
            implementation: implementationAddress,
            factory: factoryAddress
        },
        defaultProtocols: defaultProtocols.map((p, i) => ({
            address: p,
            selectors: defaultSelectors[i]
        })),
        gasUsed: {
            implementation: accountReceipt.gasUsed.toString(),
            factory: factoryReceipt.gasUsed.toString()
        }
    };

    const filename = `deployments/smart-accounts-${chain.name.toLowerCase()}.json`;
    fs.writeFileSync(filename, JSON.stringify(deployment, null, 2));

    console.log("=".repeat(60));
    console.log("✅ Smart Account System Deployed!");
    console.log("=".repeat(60));
    console.log("📍 Implementation:", implementationAddress);
    console.log("🏭 Factory:", factoryAddress);
    console.log("📁 Saved to:", filename);
    console.log();
    console.log("🔧 Next steps:");
    console.log("  1. Update backend with factory address");
    console.log("  2. Set proper SessionKey for backend signer");
    console.log("  3. Test account creation: factory.createAccount(user)");
}

main().catch(console.error);
