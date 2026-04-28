# config.py
# 配置加载器——把 YAML 配置翻译成 Python 能直接用的对象
#
# 核心职责：
# 1. 读取 system_config.yaml 文件
# 2. 把嵌套的字典变成可以用 . 访问的属性
# 3. 全局只有一个实例（单例模式）

from pathlib import Path          # 处理文件路径，比字符串拼接安全
from typing import Any            # 类型注解
import yaml                       # 读取 YAML 文件


class Config:
    """
    配置加载器——系统的"翻译官"

    类比：餐厅的中央公告板——所有服务员（Agent）都能看到，
    上面写着今天用什么食材（模型）、检查哪些标准（维度）等。

    用法：
        from config import config
        print(config.system_name)      # 输出：标书智能审核系统
        print(config.model_reasoning)  # 输出：qwen-max
    """

    def __init__(self, config_path: str = "system_config.yaml"):
        """
        初始化：加载配置文件

        参数：
            config_path: YAML 配置文件的路径，默认是项目根目录下的 system_config.yaml
        """
        # 1. 找到配置文件的绝对路径
        #    Path(__file__).parent 获取当前文件（config.py）所在的目录
        #    然后拼接配置文件名
        self._config_path = Path(__file__).parent / config_path

        # 2. 读取并解析 YAML 文件
        #    open() 打开文件，yaml.safe_load() 安全地解析 YAML 内容
        #    safe_load 比 load 安全——不会执行 YAML 中的恶意代码
        with open(self._config_path, "r", encoding="utf-8") as f:
            self._data: dict[str, Any] = yaml.safe_load(f)

    # ===== 用 @property 把字典访问变成属性访问 =====

    @property
    def system_name(self) -> str:
        """系统名称，如 '标书智能审核系统'"""
        return self._data["system"]["name"]

    @property
    def system_version(self) -> str:
        """系统版本号"""
        return self._data["system"]["version"]

    @property
    def system_description(self) -> str:
        """系统描述"""
        return self._data["system"]["description"]

    @property
    def global_rules(self) -> list[str]:
        """
        全局审核规则——所有 Agent 必须遵守的铁律

        类比：餐厅的"食品安全守则"，贴在墙上，每个厨师都要看
        """
        return self._data["global_rules"]

    @property
    def models(self) -> dict[str, dict[str, str]]:
        """
        模型配置——不同场景用什么模型

        返回格式：{"reasoning": {"name": "qwen-max", ...}, "fast": {"name": "qwen-turbo", ...}}
        """
        return self._data["models"]

    @property
    def model_reasoning(self) -> str:
        """推理模型名称——复杂判断用这个（更贵但更准）"""
        return self._data["models"]["reasoning"]["name"]

    @property
    def model_fast(self) -> str:
        """快速模型名称——简单任务用这个（便宜且快）"""
        return self._data["models"]["fast"]["name"]

    @property
    def dimensions(self) -> dict[str, dict]:
        """
        审核维度配置——完整性、合规性、报价、风险

        类比：质检员的检查清单，每个维度有不同的检查项
        """
        return self._data["dimensions"]

    @property
    def enabled_dimensions(self) -> dict[str, dict]:
        """只返回启用的审核维度"""
        return {
            key: dim
            for key, dim in self._data["dimensions"].items()
            if dim.get("enabled", False)
        }

    @property
    def scoring(self) -> dict:
        """
        评分配置——基础分和各严重程度的扣分值

        类比：考试评分标准——基础 100 分，大错扣 15 分，小错扣 1 分
        """
        return self._data["scoring"]

    @property
    def base_score(self) -> int:
        """基础分数（默认 100）"""
        return self._data["scoring"]["base_score"]

    @property
    def severity_deduction(self) -> dict[str, int]:
        """
        各严重程度的扣分值

        返回格式：{"高": 15, "中": 5, "低": 1}
        """
        return self._data["scoring"]["severity_deduction"]

    def get(self, key: str, default: Any = None) -> Any:
        """
        安全地获取配置项（类似字典的 .get() 方法）

        用法：config.get("some_key", "默认值")
        """
        return self._data.get(key, default)

    def __repr__(self) -> str:
        """打印 Config 对象时显示的信息"""
        return f"Config(system='{self.system_name}', version='{self.system_version}')"


# ===== 单例：全局唯一的配置实例 =====
# Python 的模块本身就是单例——import 多次，模块代码只执行一次
# 所以我们在这里创建实例，其他文件 import config 就能直接用

config = Config()
