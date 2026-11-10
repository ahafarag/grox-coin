// Grox dev fund addresses (consensus critical!)
//
// Every node checks that block 2 (premine) and every later block pay their
// dev fund output to the address below for that block's height. Changing an
// address, or a switch height, after launch is a hard fork.
// Addresses must be standard addresses (not subaddresses) of the right network.

#include <string>
#include "cryptonote_config.h"

namespace cryptonote
{
  // From this height on, the 5% dev fund goes to the v2 address (hard fork in v1.2.0).
  uint64_t grox_dev_fund_v2_height(network_type nettype)
  {
    switch (nettype)
    {
      case MAINNET: return 12000;
      case TESTNET: return 60;   // early, so the switch can be tested on a private testnet
      default:      return (uint64_t)-1;
    }
  }

  const std::string &grox_dev_fund_address_string(network_type nettype, uint64_t height)
  {
    static const std::string mainnet    = "G9FE1jSUU5SM3STv3PEx2kVYv5xeB5KyFh385Xgwwi9TBVBSQo6SqX7hzn4g17aJkWHhgSgnzYqgJggp2uJpHoNR13CzeqC";
    static const std::string mainnet_v2 = "GDGSHJXsxp8Y3EnLmGMnMcjLs5Qry6H5vibokRCFxKzNbZkggGkNYjd4iHwoMcJkuQKrsVN1Yt7mQY9s6AM5KVaZFLaUw5Y";
    static const std::string testnet    = "KCuAbQUVyCfiA8LYqfaUgMfFqgYLr2EWHFhmoM5VrHXWDEacoAQTXwWNRLXxWQct4t16JpQBm46JEBMD2aJkzmKP1JDoL6n"; // internal test wallet
    static const std::string testnet_v2 = "KC4orupoYt5HxaKvHsAzgSggHDCotV7VQ5MpBs9xGDwjbtpdpQ7vJcM4GC67YFvZReVfLiiUr8XXXgF5LegkrQEY2LdiWxa"; // internal test wallet 2
    static const std::string stagenet   = "GROX_STAGENET_DEV_ADDRESS_NOT_SET";
    const bool v2 = height >= grox_dev_fund_v2_height(nettype);
    switch (nettype)
    {
      case TESTNET:  return v2 ? testnet_v2 : testnet;
      case STAGENET: return stagenet;
      default:       return v2 ? mainnet_v2 : mainnet;
    }
  }
}
