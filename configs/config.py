"""配置管理模块 - 支持从 YAML 文件读取配置"""
import time
from pathlib import Path
from typing import Optional
import httpx
import functools
import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from langchain_openai import ChatOpenAI


class ModelConfig(BaseModel):
    """单个模型的配置"""

    api_type: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.0


class ConfigFile(BaseModel):
    """YAML 配置文件结构"""

    models: dict[str, ModelConfig] = {}


class Settings(BaseSettings):
    """应用配置"""

    # 当前使用的模型名称（为空则使用配置文件中的第一个模型）
    active_model: str = ""

    # 从 YAML 文件加载的配置
    _config_file: Optional[ConfigFile] = None
    _config_path: Path = Path("configs/config2.yaml")

    def load_config(self) -> None:
        """从 YAML 文件加载配置"""
        if self._config_path.exists():
            with open(self._config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._config_file = ConfigFile(**data)
        else:
            raise FileNotFoundError(
                f"配置文件不存在: {self._config_path}\n"
                f"请复制 config/config2.yaml.example 为 config/config2.yaml 并填入配置"
            )

    @property
    def current_model_config(self) -> ModelConfig:
        """获取当前模型的配置"""
        if self._config_file is None:
            self.load_config()

        # 如果未指定模型，使用第一个配置的模型（跳过 reasoner 类型）
        if not self.active_model:
            for model_name in self._config_file.models.keys():
                if "reasoner" not in model_name.lower():
                    self.active_model = model_name
                    break
            if not self.active_model:
                self.active_model = list(self._config_file.models.keys())[0]

        if self.active_model not in self._config_file.models:
            available = list(self._config_file.models.keys())
            raise ValueError(
                f"模型 '{self.active_model}' 未配置。可用模型: {available}"
            )

        return self._config_file.models[self.active_model]

    @property
    def api_key(self) -> str:
        return self.current_model_config.api_key

    @property
    def base_url(self) -> str:
        return self.current_model_config.base_url

    @property
    def model_name(self) -> str:
        return self.active_model

    @property
    def temperature(self) -> float:
        return self.current_model_config.temperature

    def list_models(self) -> list[str]:
        """列出所有可用的模型"""
        if self._config_file is None:
            self.load_config()
        return list(self._config_file.models.keys())

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()

def send_wrapper(send_func):
    @functools.wraps(send_func)
    async def send(self, *args, **kwargs):
        request = args[0]
        print(f">>> [网络发送] {request.method} {request.url} - 时间: {time.time()}")
        start_time = time.time()
        response = await send_func(request, **kwargs)
        duration = time.time() - start_time
        print(f"<<< [网络接收] {request.url} - 状态: {response.status_code} - 耗时: {duration:.2f}s - 时间: {time.time()}")
        return response
    return send

def get_llm() -> ChatOpenAI:
    client = ChatOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model_name,
        temperature=settings.temperature,
    )
    return client
