const { keccak256, RLP } = require('ethers');

const deployer = '0xa30A689ec0F9D717C5bA1098455B031b868B720f';

console.log('Calculating contract addresses for deployer:', deployer);
console.log('');

for (let n = 60; n <= 64; n++) {
    const rlpEncoded = RLP.encode([deployer, n]);
    const hash = keccak256(rlpEncoded);
    const addr = '0x' + hash.slice(-40);
    console.log(`Nonce ${n}: ${addr}`);
}
