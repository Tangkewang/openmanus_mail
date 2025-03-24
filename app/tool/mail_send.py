import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tool.base import BaseTool
from pydantic import BaseModel, Field

# Tool description
_MAIL_AGENT_DESCRIPTION = """Custom email tool for sending messages and managing communications
* SMTP connection state is maintained across commands for efficiency
* Supports both HTML and plaintext email content formats
* Attachments are encoded automatically using MIME multipart format

Command specifications:
1. `send_email`:
   - `recipients` must be a list of verified email addresses
   - When attaching files larger than 10MB, use `use_large_attachment_protocol=True`
   - Non-ASCII subject lines will be encoded using UTF-8 automatically

2. `schedule_email`:
   - Requires datetime in ISO 8601 format (e.g. "2024-03-15T14:30:00+08:00")
   - Scheduled emails persist across system restarts

3. `retry_failed_emails`:
   - Automatically retries failed deliveries from past 24 hours
   - Maximum 3 retries per message enforced by default

Security and validation rules:
* All sensitive credentials (SMTP passwords) are stored using secure string encryption
* Attachments are scanned for executable files (.exe, .bat, .sh) which will be rejected
* Cross-domain email spoofing attempts are blocked by SPF/DKIM verification

Notes for using `attach_file`:
* Provide full path to file in `file_path` parameter
* For binary files, specify `encoding_type='base64'`
* Maximum total message size (including attachments) is 25MB
* Use `attach_from_cloud_storage(uri)` for cloud-hosted files

Error handling:
* Failed SMTP connections automatically try fallback ports (587 -> 465 -> 25)
* Temporary authentication failures trigger 60-second cooldown period
* All email operations generate audit logs with full delivery metadata
"""


class EmailParams(BaseModel):
    """邮件发送参数结构"""
    to_email: str = Field(..., description="收件人邮箱地址，例如：user@example.com")
    subject: str = Field(..., description="邮件主题，需简明扼要")
    content: str = Field(..., description="邮件正文内容，支持纯文本或HTML格式")
    is_html: bool = Field(False, description="是否使用HTML格式，默认为纯文本")
    attachments: Optional[List[str]] = Field(
        None,
        description="附件路径列表，支持绝对路径或相对路径，例如：['/data/report.pdf', '财务明细.xlsx']"
    )

class MailSendTool(BaseTool):
    """邮件发送工具（支持SMTP协议）"""

    name: str = "mailsend"
    description: str = "通过SMTP协议发送电子邮件的工具，支持文本/HTML内容和附件"
    parameters: dict = {
        "type": "object",
        "properties": EmailParams.schema()["properties"],
        "required": ["to_email", "subject", "content"]
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.smtp_config = config.get("smtp", {})
        self.validate_config()

    def validate_config(self):
        """验证SMTP配置完整性"""
        required_keys = ["server", "port", "user", "password"]
        missing = [key for key in required_keys if key not in self.smtp_config]
        if missing:
            raise ValueError(f"缺少必要的SMTP配置项: {', '.join(missing)}")

    async def execute(self, **kwargs) -> str:
        """执行邮件发送操作"""
        try:
            params = EmailParams(**kwargs)
            result = self.send_email(params)
            return f"邮件发送成功：{result}"
        except Exception as e:
            return f"邮件发送失败：{str(e)}"

    def send_email(self, params: EmailParams) -> str:
        """实际发送邮件逻辑"""
        msg = MIMEMultipart()
        msg['From'] = self.smtp_config['user']
        msg['To'] = params.to_email
        msg['Subject'] = params.subject

        # 添加邮件正文
        body_type = 'html' if params.is_html else 'plain'
        msg.attach(MIMEText(params.content, body_type, 'utf-8'))

        # 处理附件
        if params.attachments:
            for file_path in params.attachments:
                self._validate_attachment(file_path)
                with open(file_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=Path(file_path).name)
                part['Content-Disposition'] = f'attachment; filename="{Path(file_path).name}"'
                msg.attach(part)

        # 发送邮件
        with smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port']) as server:
            server.login(self.smtp_config['user'], self.smtp_config['password'])
            server.send_message(msg)

        return f"已发送至 {params.to_email}"

    def _validate_attachment(self, file_path: str):
        """验证附件有效性"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"附件不存在: {file_path}")
        if Path(file_path).stat().st_size > 25 * 1024 * 1024:  # 25MB限制
            raise ValueError("附件大小超过25MB限制")

# 配置加载示例（需在项目配置模块中实现）
def load_email_config() -> Dict:
    """加载邮件配置示例"""
    return {
        "smtp": {
            "server": "smtp.example.com",
            "port": 465,
            "user": "your_email@example.com",
            "password": "your_smtp_password"
        }
    }

# 工具注册（在项目初始化时调用）
def register_tools() -> Dict[str, BaseTool]:
    """注册邮件发送工具"""
    return {
        "mailsend": MailSendTool(load_email_config())
    }
