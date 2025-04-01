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

            # 构建HTML邮件
            msg = MIMEText(content, "html")
            msg["From"] = f"openmanus <{config.mail_config.sender}>"
            # 后续发送逻辑保持不变...

        except Exception as e:
            return ToolResult(error=f"发送失败: {str(e)}")



    async def execute(self, recipient: str, subject: str, content: str, cc: List[str] = None) -> ToolResult:
        try:
            # 从配置类获取参数
            mail_config = config.mail_config

            print(mail_config)
            # 构建邮件消息
            # 修改后 (HTML格式)
            msg = MIMEText(content, "html")  # 声明HTML类型
            msg["From"] = f"OpenManus <{mail_config.sender}>"  # 添加友好名称
            msg["To"] = recipient
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ", ".join(cc)

            # 创建异步SMTP客户端
            smtp_client = aiosmtplib.SMTP(
                hostname=mail_config.server,
                port=mail_config.port,
                timeout=mail_config.timeout,
                use_tls= mail_config.use_tls
            )

            # 使用上下文管理器自动连接和关闭
            async with aiosmtplib.SMTP(
                hostname=mail_config.server,
                port=mail_config.port,
                timeout=mail_config.timeout,
                use_tls=mail_config.use_tls
            ) as smtp_client:  # 自动处理 connect() 和 quit()

                await smtp_client.login(mail_config.sender, mail_config.password)
                recipients = [recipient] + (cc or [])
                await smtp_client.send_message(msg, sender=mail_config.sender, recipients=recipients)

            return ToolResult(output=f"邮件成功发送至 {recipient}")
        except Exception as e:
            return ToolResult(error="发送失败: {str(e)}")

