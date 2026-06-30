from sui_utils import Signer
from .interfaces import Order
from .wallets import SUI_CHAIN_ID, display_address
import hashlib


class OrderSigner(Signer):
    def __init__(self, version="1.0"):
        super().__init__()
        self.version = version

    def get_order_flags(self, order):
        """0th bit = ioc
        1st bit = postOnly
        2nd bit = reduceOnly
        3rd bit  = isBuy
        4th bit = orderbookOnly
        e.g. 00000000 // all flags false
        e.g. 00000001 // ioc order, sell side, can be executed by taker
        e.e. 00010001 // same as above but can only be executed by settlement operator
        """
        flag = 0
        if order["ioc"]:
            flag += 1
        if order["postOnly"]:
            flag += 2
        if order["reduceOnly"]:
            flag += 4
        if order["isLong"]:
            flag += 8
        if order["orderbookOnly"]:
            flag += 16
        return flag

    def get_serialized_order(self, order: Order, payload_version: int = 1, wallet_chain_id: int = SUI_CHAIN_ID):
        """
        Returns order hash.
        Inputs:
            - order: the order to be signed
        Returns:
            - str: order hash
        """
        flags = self.get_order_flags(order)
        
        # Matches the Java reference implementation formatting.
        sb = []
        sb.append("{\n")
        if payload_version == 2:
            sb.append("\"action\":\"" + "PlaceOrder" + "\",\n")
        sb.append("\"market\":\"" + str(order.get("market", "")) + "\",\n")
        creator = str(order.get("creator", ""))
        if payload_version == 2:
            creator = display_address(wallet_chain_id, creator)
        sb.append("\"creator\":\"" + creator + "\",\n")
        sb.append("\"isLong\":\"" + str(order.get("isLong", False)).lower() + "\",\n")
        sb.append("\"reduceOnly\":\"" + str(order.get("reduceOnly", False)).lower() + "\",\n")
        sb.append("\"postOnly\":\"" + str(order.get("postOnly", False)).lower() + "\",\n")
        sb.append("\"orderbookOnly\":\"" + str(order.get("orderbookOnly", True)).lower() + "\",\n")
        sb.append("\"ioc\":\"" + str(order.get("ioc", False)).lower() + "\",\n")
        sb.append("\"quantity\":\"" + str(order.get("quantity", 0)) + "\",\n")
        sb.append("\"price\":\"" + str(order.get("price", 0)) + "\",\n")
        sb.append("\"leverage\":\"" + str(order.get("leverage", 0)) + "\",\n")
        sb.append("\"expiration\":\"" + str(order.get("expiration", 0)) + "\",\n")
        sb.append("\"salt\":\"" + str(order.get("salt", 0)) + "\",\n")
        sb.append("\"orderFlag\":\"" + str(flags) + "\",\n")
        sb.append("\"domain\":\"dipcoin.io\"\n")
        sb.append("}")
        
        return "".join(sb)

    def get_order_hash(self, order: Order, payload_version: int = 1, wallet_chain_id: int = SUI_CHAIN_ID):
        buffer = self.get_serialized_order(order, payload_version, wallet_chain_id)
        return hashlib.sha256(buffer).digest()

    def sign_order(self, order: Order, private_key):
        """
        Used to create an order signature. The method will use the provided key
        in params to sign the order.

        Args:
            order (Order): an order containing order fields (look at Order interface)
            private_key (str): private key of the account to be used for signing

        Returns:
            str: generated signature
        """

        buffer = self.get_serialized_order(order)
        # print("Serialized order:", buffer)
        
        # UTF-8 encode the payload.
        msg_bytearray = bytearray(buffer.encode("utf-8"))
        # print("Message length:", len(msg_bytearray))
        
        # Build intent bytes (personal message scope).
        intent = bytearray()
        
        # Prefix [3, 0, 0] for intent scope.
        intent.extend([3, 0, 0])
        
        # BCS-style length, same as Java.
        from sui_utils import decimal_to_bcs
        length_bcs = decimal_to_bcs(len(msg_bytearray))
        # print("BCS length bytes:", length_bcs)
        
        intent.extend(length_bcs)
        
        intent.extend(msg_bytearray)
        
        # print("Intent bytes:", intent.hex())
        
        msg_hash = hashlib.blake2b(intent, digest_size=32)
        # print("Message hash:", msg_hash.digest().hex())

        return self.sign_hash(msg_hash.digest(), private_key, "")

    def sign_order_with_wallet(self, order: Order, wallet, payload_version: int = 1):
        buffer = self.get_serialized_order(order, payload_version, wallet.chain_id)
        if payload_version == 1 and wallet.chain_id == SUI_CHAIN_ID:
            return self.sign_order(order, wallet.privateKeyBytes) + wallet.publicKeyBase64.decode()
        return wallet.sign_message(buffer.encode("utf-8"))
