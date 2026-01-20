import "dotenv/config";
import "@nomicfoundation/hardhat-toolbox";

/** @type import('hardhat/config').HardhatUserConfig */
export default {
    solidity: {
        version: "0.8.20",
        settings: {
            optimizer: {
                enabled: true,
                runs: 200
            },
            viaIR: true  // Enables IR-based code generation to avoid stack too deep
        }
    },
    networks: {
        base: {
            type: "http",
            url: process.env.ALCHEMY_RPC_URL || "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb",
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
            chainId: 8453
        },
        baseSepolia: {
            type: "http",
            url: "https://sepolia.base.org",
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
            chainId: 84532
        }
    },
    paths: {
        sources: "./contracts",
        tests: "./test",
        cache: "./cache",
        artifacts: "./artifacts"
    }
};
