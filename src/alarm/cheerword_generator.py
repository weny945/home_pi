"""
LLM 打气词生成器
LLM Cheerword Generator for Alarm Clock

使用 LLM 根据主题生成 30 秒左右的打气词
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# 主题提示词模板
THEME_PROMPTS = {
    "起床": "请生成一段30秒左右的起床打气词，要求：1. 充满正能量 2. 激励用户起床 3. 提及新的一天开始 4. 语言亲切自然",
    "工作": "请生成一段30秒左右的工作激励词，要求：1. 激励工作热情 2. 提及工作效率 3. 积极向上 4. 语言简洁有力",
    "运动": "请生成一段30秒左右的运动打气词，要求：1. 鼓励运动锻炼 2. 提及健康和活力 3. 充满动力 4. 语言激情澎湃",
    "学习": "请生成一段30秒左右的学习激励词，要求：1. 鼓励学习进步 2. 提及知识和成长 3. 激发求知欲 4. 语言积极正面",
    "睡觉": "请生成一段30秒左右的晚安祝福词，要求：1. 温馨舒缓 2. 提及好好休息 3. 祝愿好梦 4. 语言温柔亲切",
}


class CheerwordGenerator:
    """LLM 打气词生成器"""

    def __init__(self, llm_engine=None):
        """
        初始化打气词生成器

        Args:
            llm_engine: LLM 引擎（用于生成打气词）
        """
        self._llm_engine = llm_engine
        self._cache = {}  # 缓存已生成的打气词

    def generate_cheerword(
        self,
        theme: str = "起床",
        duration: int = 30,
        use_cache: bool = True
    ) -> str:
        """
        生成打气词

        Args:
            theme: 主题（如"起床"、"工作"、"运动"等）
            duration: 目标时长（秒）
            use_cache: 是否使用缓存

        Returns:
            str: 生成的打气词
        """
        if not self._llm_engine:
            # 如果没有 LLM 引擎，使用预设模板
            return self._get_default_cheerword(theme)

        # 检查缓存
        cache_key = f"{theme}_{duration}"
        if use_cache and cache_key in self._cache:
            logger.info(f"使用缓存的打气词: {theme}")
            return self._cache[cache_key]

        try:
            # 构建提示词
            prompt = self._build_prompt(theme, duration)

            # 调用 LLM 生成
            logger.info(f"正在生成 {theme} 主题的打气词...")
            result = self._llm_engine.chat(
                prompt,
                system_prompt="你是一个专业的语音助手，擅长创作激励人心的打气词。"
            )

            cheerword = result.get("reply", "").strip()

            if not cheerword:
                logger.warning("LLM 生成的打气词为空，使用默认模板")
                return self._get_default_cheerword(theme)

            # 缓存结果
            self._cache[cache_key] = cheerword

            logger.info(f"✅ 打气词生成成功（主题: {theme}, 长度: {len(cheerword)} 字）")
            return cheerword

        except Exception as e:
            logger.error(f"LLM 生成打气词失败: {e}")
            return self._get_default_cheerword(theme)

    def _build_prompt(self, theme: str, duration: int) -> str:
        """
        构建提示词

        Args:
            theme: 主题
            duration: 目标时长（秒）

        Returns:
            str: 提示词
        """
        # 检查是否有预设提示词
        if theme in THEME_PROMPTS:
            base_prompt = THEME_PROMPTS[theme]
        else:
            # 自定义主题
            base_prompt = f"请生成一段{duration}秒左右的'{theme}'主题打气词，要求：1. 充满正能量 2. 激励人心 3. 语言亲切自然 4. 长度控制在80-120字"

        return f"{base_prompt}\n\n请直接输出打气词内容，不要有任何其他解释或说明。"

    def _get_default_cheerword(self, theme: str) -> str:
        """
        获取默认打气词（当 LLM 不可用时）

        Args:
            theme: 主题

        Returns:
            str: 默认打气词
        """
        default_cheerwords = {
            "起床": "早上好！新的一天开始了，阳光正好，微风不燥，让我们一起迎接美好的一天！加油，你是最棒的！",
            "工作": "工作的时刻到了！保持专注，发挥你的潜力，每一分努力都不会白费。你一定可以出色地完成今天的任务！",
            "运动": "该运动了！锻炼身体，充满活力，汗水是努力的见证。让我们一起动起来，追求更健康的生活！",
            "学习": "学习的时间到了！知识的海洋在等待你探索，每一次学习都是成长的机会。保持好奇心，你一定会有收获！",
            "睡觉": "夜深了，该休息了。放下一天的疲惫，好好睡一觉，明天又是全新的一天。祝你晚安，做个好梦！"
        }

        return default_cheerwords.get(theme, f"时间到了！{theme}时刻！加油，你可以的！")

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("打气词缓存已清空")

    def get_supported_themes(self) -> list:
        """
        获取支持的主题列表

        Returns:
            list: 主题列表
        """
        return list(THEME_PROMPTS.keys())
