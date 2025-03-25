from unittest.mock import AsyncMock, MagicMock, patch

import aiosmtplib
import pytest

from app.config import MailSettings
from app.tool.mail_send import EmailSender


@pytest.fixture
def mock_mail_settings(monkeypatch):
    # 模拟 MailSettings 返回测试用配置
    mock_config = MagicMock(spec=MailSettings)
    mock_config.sender = "3188422067@qq.com"
    mock_config.password = "frojwcmveebkddhj"
    mock_config.server = "smtp.qq.com"
    mock_config.port = 587
    mock_config.timeout = 10
    mock_config.use_tls = True

    # 替换原始配置类
    monkeypatch.setattr("app.tool.email_sender.MailSettings", lambda: mock_config)
    return mock_config

@pytest.fixture
def mock_smtp_client():
    # 模拟 aiosmtplib 的 SMTP 客户端
    with patch("aiosmtplib.SMTP", new_callable=AsyncMock) as mock_smtp:
        yield mock_smtp()

@pytest.mark.asyncio
async def test_send_email_success(mock_mail_settings, mock_smtp_client):
    # 初始化工具
    sender = EmailSender()

    # 调用执行方法
    result = await sender.execute(
        recipient="user@example.com",
        subject="Test Subject",
        content="Test Content"
    )

    # 验证返回结果
    assert "邮件成功发送至 user@example.com" in result

    # 验证 SMTP 流程
    mock_smtp_client.connect.assert_awaited_once()
    mock_smtp_client.starttls.assert_awaited_once()  # 根据 use_tls 配置
    mock_smtp_client.login.assert_awaited_with("test@example.com", "test_password")
    mock_smtp_client.send_message.assert_awaited_once()
    mock_smtp_client.quit.assert_awaited_once()

@pytest.mark.asyncio
async def test_send_email_with_cc(mock_mail_settings, mock_smtp_client):
    sender = EmailSender()

    result = await sender.execute(
        recipient="user@example.com",
        subject="Test",
        content="Content",
        cc=["cc1@test.com", "cc2@test.com"]
    )

    assert "邮件成功发送至 user@example.com" in result
    mock_smtp_client.send_message.assert_awaited_once_with(
        mock_mail_settings.ANY,  # 验证邮件内容包含 Cc 头
        sender="test@example.com",
        recipients=["user@example.com", "cc1@test.com", "cc2@test.com"]
    )

@pytest.mark.asyncio
async def test_send_email_auth_failure(mock_mail_settings, mock_smtp_client):
    # 模拟登录失败
    mock_smtp_client.login.side_effect = aiosmtplib.SMTPAuthenticationError(535, b"Auth failed")

    sender = EmailSender()
    result = await sender.execute(
        recipient="user@example.com",
        subject="Test",
        content="Content"
    )

    assert "SMTP协议错误" in result
    assert "Auth failed" in result

@pytest.mark.asyncio
async def test_send_email_connection_error(mock_mail_settings, mock_smtp_client):
    # 模拟连接失败
    mock_smtp_client.connect.side_effect = aiosmtplib.SMTPConnectError(421, b"Connection timeout")

    sender = EmailSender()
    result = await sender.execute(
        recipient="user@example.com",
        subject="Test",
        content="Content"
    )

    assert "邮件发送失败" in result
    assert "Connection timeout" in result
