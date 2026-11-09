// Grox dev fund addresses (consensus critical!)
//
// Every node checks that block 2 (premine) and every later block pay their
// dev fund output to this address. Changing it after launch is a hard fork.
// Must be a standard address (not a subaddress) of the right network.

#include <string>
#include "cryptonote_config.h"

namespace cryptonote
{
  const std::string &grox_dev_fund_address_string(network_type nettype)
  {
    static const std::string mainnet  = "G9FE1jSUU5SM3STv3PEx2kVYv5xeB5KyFh385Xgwwi9TBVBSQo6SqX7hzn4g17aJkWHhgSgnzYqgJggp2uJpHoNR13CzeqC";
    static const std::string testnet  = "KCuAbQUVyCfiA8LYqfaUgMfFqgYLr2EWHFhmoM5VrHXWDEacoAQTXwWNRLXxWQct4t16JpQBm46JEBMD2aJkzmKP1JDoL6n"; // internal test wallet
    static const std::string stagenet = "GROX_STAGENET_DEV_ADDRESS_NOT_SET";
    switch (nettype)
    {
      case TESTNET:  return testnet;
      case STAGENET: return stagenet;
      default:       return mainnet;
    }
  }
}
