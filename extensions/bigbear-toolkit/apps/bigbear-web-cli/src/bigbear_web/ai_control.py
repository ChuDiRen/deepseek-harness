# -*- coding: utf-8 -*-
"""AI视觉控制，用于移动端元素定位"""
import json
import re
import time
from pathlib import Path
from typing import Tuple, List

from loguru import logger
from openai import OpenAI
from PIL import Image, ImageDraw


class AIControl:
    """AI视觉控制，用于在移动设备屏幕上查找元素"""

    def __init__(self, api_key: str, base_url: str, model: str = "qwen3.6-flash-2026-04-16"):
        """
        初始化AI控制

        Args:
            api_key: AI服务的API密钥
            base_url: AI API的基础URL
            model: 使用的模型名称
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self._load_prompts()

    def _load_prompts(self):
        """从文件加载提示词模板"""
        prompts_dir = Path(__file__).parent / "prompts"
        self._prompt_single = (prompts_dir / "single_element.txt").read_text(encoding="utf-8")
        self._prompt_batch = (prompts_dir / "batch_elements.txt").read_text(encoding="utf-8")
        self._prompt_content = (prompts_dir / "content_analysis.txt").read_text(encoding="utf-8")
        self._prompt_description = (prompts_dir / "content_description.txt").read_text(encoding="utf-8")

    def _build_prompt(self, template: str, **kwargs) -> str:
        """构建提示词，替换模板变量"""
        result = template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def find_element(self, image_base64: str, original_image: Image.Image,
                     element_info: str, element_info_enhanced: str = "",
                     max_retries: int = 3, debug: bool = False, dpr: float = 1.0) -> Tuple[float, float]:
        """
        使用AI视觉查找元素坐标

        Args:
            image_base64: Base64编码的截图
            original_image: 截图的PIL Image对象
            element_info: 要查找的元素描述
            element_info_enhanced: 增强的搜索指令
            max_retries: 最大重试次数
            debug: 是否输出调试信息

        Returns:
            (center_x, center_y) 坐标元组

        Raises:
            Exception: 如果在最大重试次数后仍无法找到元素
        """
        import sys
        if debug:
            logger.remove()
            logger.add(sys.stderr, level="DEBUG", format="{time:HH:mm:ss} | {level} | {message}", colorize=False)

        original_width, original_height = original_image.size
        step_times = {}

        for retry_count in range(max_retries):
            step_start = time.time()
            logger.debug("\n{}  {} / {} 次尝试识别元素  {}", "=" * 20, retry_count + 1, max_retries, "=" * 20)

            prompt = self._build_prompt(
                self._prompt_single,
                element_info=element_info,
                original_width=original_width,
                original_height=original_height
            )

            logger.debug('提示词内容：{}', prompt)

            try:
                step_times['构建请求'] = time.time() - step_start
                ai_start = time.time()
                completion = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.1,
                    max_tokens=1024,
                    response_format={"type": "json_object"},
                    extra_body={
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 512,
                            "mirostat": 0,
                        },
                        "stream": False,
                        "chat_template_kwargs": {
                            "enable_thinking": False
                        },
                    },
                    messages=[{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                        {"type": "text", "text": prompt}
                    ]}]
                )
                step_times['AI调用'] = time.time() - ai_start

                parse_start = time.time()
                ai_response = json.loads(completion.model_dump_json())['choices'][0]['message']['content']
                logger.debug("AI响应文本：{}", ai_response)

                pattern = r'```json\n(.*?)```'
                match = re.search(pattern, ai_response, re.DOTALL)

                if match:
                    json_content = match.group(1)
                else:
                    try:
                        json_content = json.dumps(json.loads(ai_response), ensure_ascii=False)
                    except:
                        json_content = None

                step_times['JSON解析'] = time.time() - parse_start

                if json_content:
                    parse_start2 = time.time()
                    result = json.loads(json_content)

                    if result.get('found', False):
                        bbox = result.get('bbox', [])

                        if isinstance(bbox, list) and len(bbox) == 1 and isinstance(bbox[0], list):
                            bbox = bbox[0]

                        if len(bbox) >= 4:
                            norm_start = time.time()
                            scale_x = original_width / 1000
                            scale_y = original_height / 1000

                            x1, y1, x2, y2 = (
                                bbox[0] * scale_x,
                                bbox[1] * scale_y,
                                bbox[2] * scale_x,
                                bbox[3] * scale_y
                            )
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2

                            step_times['坐标归一化'] = time.time() - norm_start
                            step_times['结果处理'] = time.time() - parse_start2

                            logger.debug("元素识别成功！归一化后 bbox: [{}, {}] 中心点: ({:.1f}, {:.1f})",
                                        int(x1), int(y1), int(x2), int(y2), center_x, center_y)

                            if debug:
                                save_start = time.time()
                                debug_image = original_image.copy()
                                debug_image = self._mark_bbox_on_image(debug_image, [int(x1), int(y1), int(x2), int(y2)], element_info)
                                debug_image.save(f"debug_element_found_{retry_count + 1}.png")
                                step_times['保存调试图像'] = time.time() - save_start
                                logger.debug("已保存标记图像: debug_element_found_{}.png", retry_count + 1)

                            total_time = sum(step_times.values())
                            logger.debug("第{}次识别耗时统计: 总计{:.3f}秒", retry_count + 1, total_time)
                            for step, duration in step_times.items():
                                percentage = (duration / total_time * 100) if total_time > 0 else 0
                                logger.debug("  - {}: {:.3f}秒 ({:.1f}%)", step, duration, percentage)

                            return center_x, center_y
                    else:
                        logger.debug("元素未找到，将尝试滚动或等待重试...")

                retry_count += 1
                if retry_count < max_retries:
                    logger.debug("进行第 {} 次重试...", retry_count + 1)

            except Exception as e:
                logger.debug("错误: {}", e)
                import traceback
                traceback.print_exc()
                retry_count += 1
                if retry_count < max_retries:
                    logger.debug("进行第 {} 次重试...", retry_count + 1)

        raise Exception(f"元素识别失败：{element_info}")

    def find_element_batch(self, image_base64: str, original_image: Image.Image,
                           elements: List[tuple],
                           debug: bool = False, dpr: float = 1.0) -> List[tuple]:
        """
        一次AI调用识别多个元素坐标

        Args:
            image_base64: Base64编码的截图
            original_image: 截图的PIL Image对象
            elements: [(element_info, element_info_enhanced), ...]
            debug: 是否输出调试信息
            dpr: 设备像素比

        Returns:
            [(element_info, x, y), ...] 成功时x,y为float，失败时为(None, None)
        """
        import sys
        if debug:
            logger.remove()
            logger.add(sys.stderr, level="DEBUG", format="{time:HH:mm:ss} | {level} | {message}", colorize=False)

        original_width, original_height = original_image.size

        # 构建元素列表字符串
        elements_list = "\n".join([f"- {elem[0]}" for elem in elements])
        prompt = self._build_prompt(
            self._prompt_batch,
            elements_list=elements_list,
            original_width=original_width,
            original_height=original_height
        )

        logger.debug('批量识别提示词：{}', prompt)

        try:
            ai_start = time.time()
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"},
                extra_body={
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1024,
                        "mirostat": 0,
                    },
                    "stream": False,
                    "chat_template_kwargs": {
                        "enable_thinking": False
                    },
                },
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                    {"type": "text", "text": prompt}
                ]}]
            )
            logger.debug("AI批量识别耗时: {:.3f}s", time.time() - ai_start)

            ai_response = json.loads(completion.model_dump_json())['choices'][0]['message']['content']
            logger.debug("AI响应文本：{}", ai_response)

            pattern = r'```json\n(.*?)```'
            match = re.search(pattern, ai_response, re.DOTALL)

            if match:
                json_content = match.group(1)
            else:
                try:
                    json_content = json.dumps(json.loads(ai_response), ensure_ascii=False)
                except:
                    json_content = None

            if not json_content:
                raise Exception("AI响应JSON解析失败")

            result = json.loads(json_content)
            elements_result = result.get('elements', [])

            # 构建结果映射
            results_map = {}
            for elem_result in elements_result:
                name = elem_result.get('name', '')
                if elem_result.get('found', False):
                    bbox = elem_result.get('bbox', [])
                    if len(bbox) >= 4:
                        scale_x = original_width / 1000
                        scale_y = original_height / 1000
                        x1, y1, x2, y2 = (
                            bbox[0] * scale_x,
                            bbox[1] * scale_y,
                            bbox[2] * scale_x,
                            bbox[3] * scale_y
                        )
                        results_map[name] = ((x1 + x2) / 2, (y1 + y2) / 2)

            # 按原始顺序返回结果
            final_results = []
            for elem_info, _ in elements:
                if elem_info in results_map:
                    x, y = results_map[elem_info]
                    final_results.append((elem_info, x, y))
                    logger.debug("识别成功: {} -> ({:.1f}, {:.1f})", elem_info, x, y)
                else:
                    final_results.append((elem_info, None, None))
                    logger.debug("识别失败: {}", elem_info)

            return final_results

        except Exception as e:
            logger.debug("批量识别错误: {}", e)
            import traceback
            traceback.print_exc()
            # 识别失败时返回全None
            return [(elem[0], None, None) for elem in elements]

    def _mark_bbox_on_image(self, image: Image.Image, bbox: list, description: str) -> Image.Image:
        """在图像上标记bbox区域"""
        draw = ImageDraw.Draw(image)
        x1, y1, x2, y2 = bbox
        draw.rectangle([x1, y1, x2, y2], outline='red', width=3)
        draw.text((x1, max(y1 - 25, 10)), f"Found: {description}", fill='red')
        return image

    def mark_element(self, image: Image.Image, bbox: list, output_path: str, description: str):
        """在图像上标记元素用于调试"""
        marked_image = self._mark_bbox_on_image(image, bbox, description)
        marked_image.save(output_path)

    def get_content_ai(self, image_base64: str, original_image: Image.Image,
                        description: str, debug: bool = False) -> dict:
        """
        根据文字描述获取截图中对应区域的内容

        Args:
            image_base64: Base64编码的截图
            original_image: 截图的PIL Image对象
            description: 要获取内容的文字描述（如"标题下方的正文"）
            debug: 是否输出调试信息

        Returns:
            包含区域坐标和内容的字典 {"bbox": [x1,y1,x2,y2], "content": "识别内容"}
        """
        import sys
        logger.remove()
        if debug:
            logger.add(sys.stderr, level="DEBUG", format="{time:HH:mm:ss} | {level} | {message}", colorize=False)
        else:
            logger.add(sys.stderr, level="WARNING", format="{time:HH:mm:ss} | {level} | {message}", colorize=False)

        original_width, original_height = original_image.size

        prompt = self._build_prompt(
            self._prompt_content,
            description=description,
            original_width=original_width,
            original_height=original_height
        )

        logger.debug('OCR提示词：{}', prompt)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"},
                extra_body={
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1024,
                        "mirostat": 0,
                    },
                    "stream": False,
                    "chat_template_kwargs": {
                        "enable_thinking": False
                    },
                },
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                    {"type": "text", "text": prompt}
                ]}]
            )

            ai_response = json.loads(completion.model_dump_json())['choices'][0]['message']['content']
            logger.debug("AI响应文本：{}", ai_response)

            pattern = r'```json\n(.*?)```'
            match = re.search(pattern, ai_response, re.DOTALL)

            if match:
                json_content = match.group(1)
            else:
                try:
                    json_content = json.dumps(json.loads(ai_response), ensure_ascii=False)
                except:
                    json_content = None

            if json_content:
                result = json.loads(json_content)

                if isinstance(result, list):
                    if len(result) >= 2:
                        bbox = result[0]
                        content = result[1]
                        result = {"bbox": bbox, "content": content}
                    else:
                        raise Exception("AI响应格式错误")

                bbox = result.get('bbox', [])

                if isinstance(bbox, list) and len(bbox) == 1 and isinstance(bbox[0], list):
                    bbox = bbox[0]

                if len(bbox) >= 4:
                    scale_x = original_width / 1000
                    scale_y = original_height / 1000
                    x1, y1, x2, y2 = (
                        bbox[0] * scale_x,
                        bbox[1] * scale_y,
                        bbox[2] * scale_x,
                        bbox[3] * scale_y
                    )
                    result['bbox'] = [int(x1), int(y1), int(x2), int(y2)]
                    logger.debug("区域定位成功: bbox={}", result['bbox'])
                    return result

            raise Exception("AI响应格式错误")

        except Exception as e:
            logger.debug("内容识别错误: {}", e)
            raise Exception(f"内容识别失败：{e}")

    # ---------- 区域结构化描述 ----------

    def describe_region_ai(self, image_base64: str, original_image: Image.Image,
                           description: str, debug: bool = False) -> dict:
        """根据描述获取截图中对应区域的结构化描述（不含坐标）

        与 get_content_ai 的区别：本方法返回区域的结构化描述（layout/icons/text/intro），
        不返回 bbox。专供 `get` 命令使用，不应被 scroll --region 等需要坐标的调用方使用。

        Args:
            image_base64: Base64 编码的截图
            original_image: 截图的 PIL Image 对象
            description: 区域描述，如"验证码区域"
            debug: 是否输出调试信息

        Returns:
            {"description": {"layout": str, "icons": list, "text": str, "intro": str}}
            若 AI 响应缺 description 字段，返回 {"description": {}}
        """
        import sys
        logger.remove()
        if debug:
            logger.add(sys.stderr, level="DEBUG", format="{time:HH:mm:ss} | {level} | {message}", colorize=False)
        else:
            logger.add(sys.stderr, level="WARNING", format="{time:HH:mm:ss} | {level} | {message}", colorize=False)

        original_width, original_height = original_image.size
        prompt = self._build_prompt(
            self._prompt_description,
            description=description,
            original_width=original_width,
            original_height=original_height,
        )

        logger.debug('区域描述提示词：{}', prompt)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
                extra_body={
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 512,
                        "mirostat": 0,
                    },
                    "stream": False,
                    "chat_template_kwargs": {
                        "enable_thinking": False
                    },
                },
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                    {"type": "text", "text": prompt}
                ]}]
            )

            ai_response = json.loads(completion.model_dump_json())['choices'][0]['message']['content']
            logger.debug("AI响应文本：{}", ai_response)

            pattern = r'```json\n(.*?)```'
            match = re.search(pattern, ai_response, re.DOTALL)

            if match:
                json_content = match.group(1)
            else:
                try:
                    json_content = json.dumps(json.loads(ai_response), ensure_ascii=False)
                except Exception:
                    json_content = None

            if json_content:
                result = json.loads(json_content)

                # 容忍 AI 漏掉 description 字段（不要因为字段缺失抛错）
                if not isinstance(result, dict):
                    return {"description": {}}
                if "description" not in result:
                    return {"description": {}}

                # 确保 description 是 dict
                desc = result["description"]
                if not isinstance(desc, dict):
                    desc = {}
                result["description"] = desc

                logger.debug("区域描述成功: {}", result["description"])
                return result

            raise Exception("AI响应格式错误")

        except Exception as e:
            logger.debug("区域描述错误: {}", e)
            raise Exception(f"内容识别失败：{e}")
