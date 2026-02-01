// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/proxy/Clones.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title TechneAgentFactory
 * @notice Factory for deploying TechneAgentAccount smart accounts
 * @dev Uses EIP-1167 minimal proxy pattern for gas-efficient deployments
 * 
 * ERC-8004 ARCHITECTURE (1 Agent = 1 Wallet):
 * - Each agent gets its own unique Smart Account
 * - 1 owner (user wallet) can have MULTIPLE agent accounts
 * - agentSalt = keccak256(agentId) for deterministic CREATE2 addresses
 * - Auto-whitelist common protocols on creation
 * - Gas-efficient: ~100K gas per deployment vs 2M for full contract
 */
contract TechneAgentFactory is Ownable {
    using Clones for address;

    // ============ State ============
    address public immutable implementation;
    
    // Owner -> AgentSalt -> Smart Account (1 agent = 1 wallet)
    mapping(address => mapping(uint256 => address)) public accounts;
    
    // Owner -> All their agent accounts
    mapping(address => address[]) public ownerAccounts;
    
    // All deployed accounts (for iteration)
    address[] public allAccounts;
    
    // Default session key to add (Techne backend)
    address public defaultSessionKey;
    uint48 public defaultSessionKeyValidity = 365 days;
    uint256 public defaultDailyLimitUSD = 1_000_000 * 1e8; // $1M/day
    
    // Default protocols to whitelist
    address[] public defaultProtocols;
    bytes4[][] public defaultSelectors;

    // ============ Events ============
    event AccountCreated(
        address indexed owner,
        address indexed account,
        uint256 indexed agentSalt
    );
    event DefaultSessionKeySet(address indexed key, uint48 validity, uint256 dailyLimit);
    event DefaultProtocolsUpdated(uint256 count);

    // ============ Errors ============
    error InvalidOwner();
    error ZeroAddress();

    // ============ Constructor ============
    constructor(
        address _implementation,
        address _defaultSessionKey
    ) Ownable(msg.sender) {
        if (_implementation == address(0)) revert ZeroAddress();
        implementation = _implementation;
        defaultSessionKey = _defaultSessionKey;
    }

    // ============ Factory Functions ============

    /**
     * @notice Create a new smart account for a specific agent
     * @param owner The owner of the new account (user's EOA)
     * @param agentSalt Unique salt per agent (e.g., keccak256(agentId))
     * @return account The deployed smart account address
     * 
     * ERC-8004 ARCHITECTURE:
     * - 1 owner can have MULTIPLE agents
     * - Each agent has its own Smart Account
     * - agentSalt = keccak256(agentId) for deterministic addressing
     */
    function createAccount(address owner, uint256 agentSalt) external returns (address account) {
        if (owner == address(0)) revert InvalidOwner();
        
        // Check if this specific agent already has account
        if (accounts[owner][agentSalt] != address(0)) {
            return accounts[owner][agentSalt]; // Return existing, don't revert
        }

        // Deploy deterministic clone with combined salt
        bytes32 salt = keccak256(abi.encodePacked(owner, agentSalt));
        account = implementation.cloneDeterministic(salt);

        // Initialize the account
        ITechneAgentAccount(account).initialize(owner);

        // Add default session key if configured
        if (defaultSessionKey != address(0)) {
            ITechneAgentAccount(account).addSessionKey(
                defaultSessionKey,
                uint48(block.timestamp) + defaultSessionKeyValidity,
                defaultDailyLimitUSD
            );
        }

        // Whitelist default protocols
        if (defaultProtocols.length > 0) {
            ITechneAgentAccount(account).batchWhitelist(
                defaultProtocols,
                defaultSelectors
            );
        }

        // Register account
        accounts[owner][agentSalt] = account;
        ownerAccounts[owner].push(account);
        allAccounts.push(account);

        emit AccountCreated(owner, account, agentSalt);
    }

    /**
     * @notice Legacy: Create account with default salt (0)
     * @param owner The owner of the new account
     */
    function createAccount(address owner) external returns (address) {
        return this.createAccount(owner, 0);
    }

    /**
     * @notice Get deterministic address for owner + agent (without deploying)
     * @param owner The owner address
     * @param agentSalt The agent's unique salt
     */
    function getAddress(address owner, uint256 agentSalt) external view returns (address) {
        bytes32 salt = keccak256(abi.encodePacked(owner, agentSalt));
        return implementation.predictDeterministicAddress(salt, address(this));
    }

    /**
     * @notice Legacy: Get address with default salt
     */
    function getAddress(address owner) external view returns (address) {
        return this.getAddress(owner, 0);
    }

    /**
     * @notice Check if specific agent account exists
     */
    function hasAccount(address owner, uint256 agentSalt) external view returns (bool) {
        return accounts[owner][agentSalt] != address(0);
    }

    /**
     * @notice Legacy: Check if default account exists
     */
    function hasAccount(address owner) external view returns (bool) {
        return accounts[owner][0] != address(0);
    }

    /**
     * @notice Get all accounts for an owner
     */
    function getAccountsForOwner(address owner) external view returns (address[] memory) {
        return ownerAccounts[owner];
    }

    /**
     * @notice Get account count for an owner
     */
    function getAccountCount(address owner) external view returns (uint256) {
        return ownerAccounts[owner].length;
    }

    /**
     * @notice Get total number of accounts created
     */
    function totalAccounts() external view returns (uint256) {
        return allAccounts.length;
    }

    // ============ Admin Functions ============


    /**
     * @notice Set default session key for new accounts
     * @dev Only owner. Used to pre-configure Techne backend access.
     */
    function setDefaultSessionKey(
        address key,
        uint48 validity,
        uint256 dailyLimitUSD
    ) external onlyOwner {
        defaultSessionKey = key;
        defaultSessionKeyValidity = validity;
        defaultDailyLimitUSD = dailyLimitUSD;
        emit DefaultSessionKeySet(key, validity, dailyLimitUSD);
    }

    /**
     * @notice Set default protocols to whitelist for new accounts
     * @dev Only owner. Pre-configures Aave, Aerodrome, etc.
     */
    function setDefaultProtocols(
        address[] calldata protocols,
        bytes4[][] calldata selectors
    ) external onlyOwner {
        require(protocols.length == selectors.length, "Length mismatch");
        
        delete defaultProtocols;
        delete defaultSelectors;
        
        for (uint256 i = 0; i < protocols.length; i++) {
            defaultProtocols.push(protocols[i]);
            defaultSelectors.push(selectors[i]);
        }
        
        emit DefaultProtocolsUpdated(protocols.length);
    }

    /**
     * @notice Get all default protocols
     */
    function getDefaultProtocols() external view returns (
        address[] memory protocols,
        bytes4[][] memory selectors
    ) {
        return (defaultProtocols, defaultSelectors);
    }
}

// ============ Interface ============

interface ITechneAgentAccount {
    function initialize(address owner) external;
    function addSessionKey(address key, uint48 validUntil, uint256 dailyLimitUSD) external;
    function batchWhitelist(address[] calldata protocols, bytes4[][] calldata selectors) external;
}
