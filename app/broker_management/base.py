from abc import ABC, abstractmethod


class BaseBrokerAdapter(ABC):

    @abstractmethod
    def connect(self, **kwargs) -> bool: ...

    @abstractmethod
    def validate_session(self) -> bool: ...

    @abstractmethod
    def get_balance(self) -> dict: ...

    @abstractmethod
    def get_orders(self) -> list: ...

    @abstractmethod
    def get_positions(self) -> list: ...

    @abstractmethod
    def place_order(self, order_params: dict): ...