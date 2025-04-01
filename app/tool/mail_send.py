from email.mime.text import MIMEText
from typing import List

import aiosmtplib
from app.config import config  # 导入配置类
from app.tool.base import BaseTool, ToolResult


class EmailSender(BaseTool):
    name: str = "email_sender"
    description: str = """异步邮件发送工具，支持SMTP协议。邮件内容处理规则：
1. 称呼智能处理：
   - 当正文开头有类似「尊敬的...」时保留原称呼
   - 无称呼时自动添加「尊敬的先生/女士」
2. 系统自动增强内容：
   - 自动添加品牌签名「openmanus」
   - 注入响应式邮件样式
3. 强制要求：
   - 必须使用完整HTML结构
   - 禁止任何占位符"""

    parameters: dict = {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "收件人邮箱地址（多个地址用英文分号分隔）"
            },
            "subject": {
                "type": "string",
                "description": "邮件主题（长度建议不超过120字符）"
            },
            "content": {
                "type": "string",
                "description": "邮件HTML正文（支持CSS样式），需遵守以下规则：\n"
                             "- 禁止使用[发件人姓名]、XXX等占位符\n"
                             "需使用{name}表示发件方，系统将自动替换为openmanus\n"
                             "- 称呼请直接写「尊敬的先生/女士」\n"
                             "要求格式要精美"
            },
            "cc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "抄送邮箱列表（可选）"
            }
        },
        "required": ["recipient", "subject", "content"]
    }


    async def execute(self, recipient: str, subject: str, content: str, cc: List[str] = None) -> ToolResult:
        try:
            # 自动化内容替换
            content = (
                content.replace("{name}", "openmanus")
                .replace("尊敬的XXX", "尊敬的先生/女士")
            )

            # 处理多收件人逻辑
            recipient_list = [addr.strip() for addr in recipient.split(';') if addr.strip()]
            if not recipient_list:
                return ToolResult(error="收件人地址不能为空")

            # 从配置类获取参数
            mail_config = config.mail_config

            # 构建邮件消息
            msg = MIMEText(content, "html")
            msg["From"] = f"OpenManus <{mail_config.sender}>"
            msg["To"] = ", ".join(recipient_list)  # 标准邮件格式用逗号分隔
            msg["Subject"] = subject

            if cc:
                msg["Cc"] = ", ".join(cc)

            # 创建异步SMTP客户端
            async with aiosmtplib.SMTP(
                hostname=mail_config.server,
                port=mail_config.port,
                timeout=mail_config.timeout,
                use_tls=mail_config.use_tls
            ) as smtp_client:
                await smtp_client.login(mail_config.sender, mail_config.password)

                # 合并收件人列表（包含CC）
                all_recipients = recipient_list + (cc or [])
                await smtp_client.send_message(
                    msg,
                    sender=mail_config.sender,
                    recipients=all_recipients
                )

            return ToolResult(output=f"邮件成功发送至 {len(all_recipients)} 个收件人")

        except Exception as e:
            return ToolResult(error=f"发送失败: {str(e)}")


