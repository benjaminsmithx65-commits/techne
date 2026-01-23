require("dotenv").config();
require("@nomicfoundation/hardhat-ethers");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
    solidity: {
        compilers: [
            {
                version: "0.8.20",
                settings: {
                    optimizer: { enabled: true, runs: 200 },
                    viaIR: true
                }
            },
            {
                version: "0.8.24",
                settings: {
                    optimizer: { enabled: true, runs: 200 },
                    viaIR: true
                }
            }
        ]
    },
    networks: {
        base: {
            url: process.env.ALCHEMY_RPC_URL || "https://mainnet.base.org",
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
            chainId: 8453
        },
        baseSepolia: {
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
