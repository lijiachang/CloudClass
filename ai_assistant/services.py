import json
import os
from difflib import SequenceMatcher
from urllib import error, request

from assignments.models import AssignmentSubmission


class TeacherAIService:
    api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model = "qwen-plus"

    MODE_INSTRUCTIONS = {
        "lesson_prep": "你是一名高校课程助教，请输出备课建议，包含教学目标、知识点大纲、课堂活动和课后建议。",
        "lesson_teaching": "你是一名高校课堂助教，请输出授课提纲，包含讲解步骤、互动提问和随堂练习。",
        "evaluation": "你是一名高校教师助教，请针对学生表现输出评价草稿和改进建议。",
        "grading": "你是一名严谨的助教，请基于作业要求给出建议分数、评分依据和教师评语草稿。",
    }

    @classmethod
    def generate(cls, mode, prompt):
        instruction = cls.MODE_INSTRUCTIONS.get(mode)
        if not instruction:
            raise ValueError("不支持的 AI 模式")

        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            return cls._build_demo_response(mode, prompt, "未检测到 DASHSCOPE_API_KEY，当前返回本地演示建议。")

        payload = {
            "model": os.getenv("DASHSCOPE_MODEL", cls.model),
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }
        req = request.Request(
            cls.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return cls._build_demo_response(mode, prompt, "千问调用失败，当前返回本地演示建议。")

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
        if not content:
            return cls._build_demo_response(mode, prompt, "千问暂未返回有效结果，当前返回本地演示建议。")
        return {"content": content, "notice": "结果由千问生成，仅供教师参考。"}

    @classmethod
    def student_chat(cls, question):
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            return {
                "content": (
                    "这是学生 AI 聊天的本地演示回复。\n"
                    "你可以继续追问课程重点、作业思路、知识点解释、复习建议等内容。\n"
                    f"本次问题参考：{question.strip()[:180] or '未提供问题'}"
                ),
                "notice": "未检测到 DASHSCOPE_API_KEY，当前返回本地演示回复。",
            }

        payload = {
            "model": os.getenv("DASHSCOPE_MODEL", cls.model),
            "messages": [
                {
                    "role": "system",
                    "content": "你是一名面向大学生的课程学习助手，请用通俗、友好的中文回答问题，帮助学生理解课程内容。",
                },
                {"role": "user", "content": question},
            ],
            "temperature": 0.6,
        }
        req = request.Request(
            cls.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return {
                "content": (
                    "千问暂时不可用，当前返回本地演示回复。\n"
                    "建议你从课程目标、知识点、作业要求这几个角度继续整理问题，再和老师确认。"
                ),
                "notice": "千问调用失败，当前返回本地演示回复。",
            }

        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            return {
                "content": "当前没有拿到有效回复，你可以换个问法再试一次。",
                "notice": "千问暂未返回有效结果。",
            }
        return {"content": content, "notice": "结果由千问生成，仅供学习参考。"}

    @classmethod
    def analyze_similarity(cls, assignment):
        submissions = list(
            AssignmentSubmission.objects.filter(assignment=assignment).select_related("student").order_by("student__username")
        )
        pairs = []
        for index, left in enumerate(submissions):
            for right in submissions[index + 1 :]:
                left_text = (left.content or "").strip()
                right_text = (right.content or "").strip()
                if not left_text or not right_text:
                    continue
                ratio = SequenceMatcher(None, left_text, right_text).ratio()
                if ratio >= 0.55:
                    pairs.append(
                        {
                            "left": left,
                            "right": right,
                            "ratio": round(ratio * 100, 1),
                            "summary": "两份文本存在较高相似度，建议教师进一步人工核查。",
                        }
                    )
        if not pairs:
            return {
                "content": "未发现高相似度提交，建议仍结合附件与答题结构进行人工复核。",
                "pairs": [],
                "notice": "查重基于文本相似度计算，仅供教师参考。",
            }
        lines = [
            f"{item['left'].student.full_name} 与 {item['right'].student.full_name} 相似度约 {item['ratio']}%"
            for item in pairs
        ]
        return {
            "content": "\n".join(lines),
            "pairs": pairs,
            "notice": "查重基于文本相似度计算，仅供教师参考。",
        }

    @classmethod
    def _build_demo_response(cls, mode, prompt, notice):
        short_prompt = prompt.strip()[:180] or "未提供具体内容"
        templates = {
            "lesson_prep": (
                "1. 教学目标：明确本节课核心能力与产出。\n"
                "2. 知识点大纲：按基础概念、案例演示、课堂练习展开。\n"
                "3. 课堂活动：安排 1 次提问互动和 1 次小练习。\n"
                f"4. 结合你的输入继续完善：{short_prompt}"
            ),
            "lesson_teaching": (
                "1. 导入：用实际场景引出主题。\n"
                "2. 讲授：按知识点逐步讲解并穿插示例。\n"
                "3. 互动：准备 3 个课堂提问和 1 个随堂练习。\n"
                f"4. 当前授课重点：{short_prompt}"
            ),
            "evaluation": (
                "1. 学习表现：整体完成度较好，能围绕任务要求展开。\n"
                "2. 优点：结构清晰，关键知识点覆盖较完整。\n"
                "3. 建议：补充案例分析与个人思考，提升深度。\n"
                f"4. 评价依据参考：{short_prompt}"
            ),
            "grading": (
                "建议分数：88 分\n"
                "评分依据：完成了主要要求，结构较清晰，但分析深度仍有提升空间。\n"
                "教师评语：整体完成较好，建议补充案例论证，并进一步展开关键步骤说明。\n"
                f"参考内容：{short_prompt}"
            ),
        }
        return {"content": templates[mode], "notice": notice}
