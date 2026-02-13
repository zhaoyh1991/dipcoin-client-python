from sui_utils import numberToHex, hexToByteArray, Signer,BCSSerializer
from .interfaces import Order
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

    def get_serialized_order(self, order: Order):
        """
        Returns order hash.
        Inputs:
            - order: the order to be signed
        Returns:
            - str: order hash
        """
        flags = self.get_order_flags(order)
        
        # 严格按照 Java 代码格式实现
        sb = []
        sb.append("{\n")
        sb.append("\"market\":\"" + str(order.get("market", "")) + "\",\n")
        sb.append("\"creator\":\"" + str(order.get("creator", "")) + "\",\n")
        sb.append("\"isLong\":\"" + str(order.get("isLong", False)).lower() + "\",\n")
        sb.append("\"reduceOnly\":\"" + str(order.get("reduceOnly", False)).lower() + "\",\n")
        sb.append("\"postOnly\":\"" + "false" + "\",\n")
        sb.append("\"orderbookOnly\":\"" + "true" + "\",\n")
        sb.append("\"ioc\":\"" + "false" + "\",\n")
        sb.append("\"quantity\":\"" + str(order.get("quantity", 0)) + "\",\n")
        sb.append("\"price\":\"" + str(order.get("price", 0)) + "\",\n")
        sb.append("\"leverage\":\"" + str(order.get("leverage", 0)) + "\",\n")
        sb.append("\"expiration\":\"" + str(order.get("expiration", 0)) + "\",\n")
        sb.append("\"salt\":\"" + str(order.get("salt", 0)) + "\",\n")
        sb.append("\"orderFlag\":\"" + str(flags) + "\",\n")
        sb.append("\"domain\":\"dipcoin.io\"\n")
        sb.append("}")
        
        return "".join(sb)

    def get_order_hash(self, order: Order):
        buffer = self.get_serialized_order(order)
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
        
        # 将字符串转换为 UTF-8 字节数组
        msg_bytearray = bytearray(buffer.encode("utf-8"))
        # print("Message length:", len(msg_bytearray))
        
        # 创建 intent 字节数组
        intent = bytearray()
        
        # 添加 [3, 0, 0] 前缀
        intent.extend([3, 0, 0])
        
        # 使用与 Java 相同的 BCS 编码方式
        from sui_utils import decimal_to_bcs
        length_bcs = decimal_to_bcs(len(msg_bytearray))
        # print("BCS length bytes:", length_bcs)
        
        # 添加 BCS 编码的长度
        intent.extend(length_bcs)
        
        # 添加消息内容
        intent.extend(msg_bytearray)
        
        # print("Intent bytes:", intent.hex())
        
        # 计算 Blake2b 哈希
        msg_hash = hashlib.blake2b(intent, digest_size=32)
        # print("Message hash:", msg_hash.digest().hex())

        return self.sign_hash(msg_hash.digest(), private_key, "")
