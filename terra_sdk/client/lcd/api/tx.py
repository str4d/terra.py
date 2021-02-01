from ._base import BaseAPI
from typing import List, Optional, Union

__all__ = ["TxAPI"]

from terra_sdk.core.auth import *
from terra_sdk.core.broadcast import *
from terra_sdk.core import Numeric, Coins, Coin
from terra_sdk.core.msg import Msg
from terra_sdk.util.hash import hash_amino


class TxAPI(BaseAPI):
    async def tx_info(self, tx_hash: str) -> TxInfo:
        return TxInfo.from_data(await self._c._get(f"/txs/{tx_hash}", raw=True))

    async def create(
        self,
        source_address: str,
        msgs: List[Msg],
        fee: Optional[StdFee] = None,
        memo: str = "",
        gas_prices: Optional[Coins.Input] = None,
        gas_adjustment: Optional[Numeric.Input] = None,
        account_number: Optional[int] = None,
        sequence: Optional[int] = None,
    ) -> StdSignMsg:
        if fee is None:
            # create the fake fee
            balance = await self._c.bank.balance(source_address)
            balance_one = [Coin(c.denom, 1) for c in balance]

            # estimate the fee
            tx = StdTx(msgs, StdFee(0, balance_one), [], memo)
            fee = await self.estimate_fee(tx, gas_prices, gas_adjustment)

        if account_number is None or sequence is None:
            account = await self._c.auth.account_info(source_address)
            if account_number is None:
                account_number = account.account_number
            if sequence is None:
                sequence = account.sequence

        return StdSignMsg(
            self._c.chain_id, account_number or 0, sequence or 0, fee, msgs, memo
        )

    async def estimate_fee(
        self,
        tx: Union[StdSignMsg, StdTx],
        gas_prices: Optional[Coins.Input] = None,
        gas_adjustment: Optional[Numeric.Input] = None,
    ) -> StdFee:
        gas_prices = gas_prices or self._c.gas_prices
        gas_adjustment = gas_adjustment or self._c.gas_adjustment

        if isinstance(tx, StdSignMsg):
            tx_value = tx.to_stdtx().to_data()["value"]
        else:
            tx_value = tx.to_data()["value"]

        tx_value["fee"]["gas"] = "0"

        data = {
            "tx": tx_value,
            "gas_prices": gas_prices and Coins(gas_prices).to_data(),
            "gas_adjustment": gas_adjustment and str(gas_adjustment),
        }

        res = await self._c._post("/txs/estimate_fee", data)
        return StdFee(int(res["gas"]), Coins.from_data(res["fees"]))

    async def encode(self, tx: StdTx) -> str:
        res = await self._c._post("/txs/encode", tx.to_data())
        return res["tx"]

    async def hash(self, tx: StdTx) -> str:
        amino = await self.encode(tx)
        return hash_amino(amino)

    async def _broadcast(self, tx: StdTx, mode: str) -> dict:
        data = {"tx": tx.to_data()["value"], "mode": mode}
        return await self._c._post("/txs", data, raw=True)

    async def broadcast_sync(self, tx: StdTx):
        res = await self._broadcast(tx, "sync")
        return SyncTxBroadcastResult(
            height=res["height"],
            txhash=res["txhash"],
            raw_log=res["raw_log"],
            code=res.get("code"),
            codespace=res.get("codespace"),
        )

    async def broadcast_async(self, tx: StdTx):
        res = await self._broadcast(tx, "async")
        return AsyncTxBroadcastResult(
            height=res["height"],
            txhash=res["txhash"],
        )

    async def broadcast(self, tx: StdTx):
        res = await self._broadcast(tx, "block")
        return BlockTxBroadcastResult(
            height=res["height"],
            txhash=res["txhash"],
            raw_log=res["raw_log"],
            gas_wanted=res["gas_wanted"],
            gas_used=res["gas_used"],
            logs=res.get("logs"),
            code=res.get("code"),
            codespace=res.get("codespace"),
        )

    async def search(self, options: dict = {}) -> dict:
        res = await self._c._get("/txs", options, raw=True)
        return res
