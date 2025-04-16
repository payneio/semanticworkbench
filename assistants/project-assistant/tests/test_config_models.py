"""
Tests for the configuration models.
"""

from unittest.mock import MagicMock, patch

# Mock the openai_client.ServiceConfig
mock_service_config = MagicMock()
mock_service_config.service_type = "openai"
with patch("openai_client.ServiceConfig", MagicMock()) as MockServiceConfig:
    # After patching, import the modules
    from assistant.configs.base import (
        BaseCoordinatorConfig,
        BaseTeamConfig,
        RequestConfig,
    )
    from assistant.configs.default import (
        AssistantConfigModel,
        CoordinatorConfig,
        TeamConfig,
    )
    from assistant.configs.context_transfer import (
        ContextTransferConfigModel,
        ContextTransferCoordinatorConfig,
        ContextTransferTeamConfig,
    )


class TestBaseConfigs:
    """Tests for the base configuration classes."""

    def test_request_config(self):
        """Test RequestConfig validation."""
        # Test default values
        config = RequestConfig()
        assert config.max_tokens == 50_000
        assert config.response_tokens == 4_048
        assert config.openai_model == "gpt-4o"

        # Test setting values
        config = RequestConfig(max_tokens=100_000, response_tokens=2_000, openai_model="gpt-4o-mini")
        assert config.max_tokens == 100_000
        assert config.response_tokens == 2_000
        assert config.openai_model == "gpt-4o-mini"

    def test_base_coordinator_config(self):
        """Test BaseCoordinatorConfig validation."""
        # Test default values
        config = BaseCoordinatorConfig()
        assert "Welcome to the Project Assistant" in config.welcome_message
        assert "{share_url}" in config.welcome_message
        assert config.list_participants_command == "list-participants"

    def test_base_team_config(self):
        """Test BaseTeamConfig validation."""
        # Test default values
        config = BaseTeamConfig()
        assert "Welcome to Your Team Conversation" in config.welcome_message
        assert config.status_command == "project-status"


class TestDefaultConfigs:
    """Tests for the default configuration classes."""

    def test_coordinator_config(self):
        """Test CoordinatorConfig validation."""
        # Test default values - should inherit from base
        config = CoordinatorConfig()
        assert "Welcome to the Project Assistant" in config.welcome_message

        # Test inherited behavior
        base_config = BaseCoordinatorConfig()
        assert config.welcome_message == base_config.welcome_message

    def test_team_config(self):
        """Test TeamConfig validation."""
        # Test default values - should inherit from base
        config = TeamConfig()
        assert "Welcome to Your Team Conversation" in config.welcome_message

        # Test inherited behavior
        base_config = BaseTeamConfig()
        assert config.welcome_message == base_config.welcome_message

    @patch("openai_client.ServiceConfig", MagicMock())
    def test_assistant_config_model(self):
        """Test AssistantConfigModel validation."""
        # Test default values
        with patch("openai_client.ServiceConfig") as MockServiceConfig:
            mock_service_config = MagicMock()
            mock_service_config.service_type = "openai"
            MockServiceConfig.return_value = mock_service_config

            config = AssistantConfigModel(service_config=mock_service_config)
        assert "You are an AI project assistant" in config.instruction_prompt
        assert config.track_progress is True
        assert config.auto_sync_files is True
        assert config.proactive_guidance is True

        # Test coordinator and team configs are set
        assert isinstance(config.coordinator_config, BaseCoordinatorConfig)
        assert isinstance(config.team_config, BaseTeamConfig)


class TestContextTransferConfigs:
    """Tests for the context transfer configuration classes."""

    def test_context_transfer_coordinator_config(self):
        """Test ContextTransferCoordinatorConfig validation."""
        # Test default values
        config = ContextTransferCoordinatorConfig()
        assert "Welcome to Context Transfer" in config.welcome_message
        assert "knowledge bridge" in config.welcome_message
        assert "Explore Knowledge Space" in config.welcome_message
        assert "To begin building a comprehensive knowledge space" in config.prompt_for_files

    def test_context_transfer_team_config(self):
        """Test ContextTransferTeamConfig validation."""
        # Test default values
        config = ContextTransferTeamConfig()
        assert "Welcome to the Knowledge Space" in config.welcome_message
        assert config.status_command == "knowledge-status"

    @patch("openai_client.ServiceConfig", MagicMock())
    def test_context_transfer_config_model(self):
        """Test ContextTransferConfigModel validation."""
        # Test default values
        with patch("openai_client.ServiceConfig") as MockServiceConfig:
            mock_service_config = MagicMock()
            mock_service_config.service_type = "openai"
            MockServiceConfig.return_value = mock_service_config

            config = ContextTransferConfigModel(service_config=mock_service_config)
        assert "context transfer assistant" in config.instruction_prompt
        assert config.track_progress is False  # Key indicator for context transfer
        assert config.auto_sync_files is True
        assert config.proactive_guidance is True

        # Test request config has higher limits
        assert config.request_config.max_tokens == 128_000
        assert config.request_config.response_tokens == 16_384

        # Test coordinator and team configs are set to context transfer versions
        assert isinstance(config.coordinator_config, BaseCoordinatorConfig)
        assert isinstance(config.team_config, BaseTeamConfig)
        assert "Welcome to Context Transfer" in config.coordinator_config.welcome_message
        assert "Welcome to the Knowledge Space" in config.team_config.welcome_message


class TestConfigTemplateIntegration:
    """Test that configuration models work correctly with template detection."""

    @patch("openai_client.ServiceConfig", MagicMock())
    def test_template_identification(self):
        """Test that templates can be identified by key indicators."""
        # Create mock service config
        mock_service_config = MagicMock()
        mock_service_config.service_type = "openai"

        # Default template has track_progress = True
        with patch("openai_client.ServiceConfig") as MockServiceConfig:
            MockServiceConfig.return_value = mock_service_config
            default_config = AssistantConfigModel(service_config=mock_service_config)
            assert default_config.track_progress is True

        # Context transfer template has track_progress = False
        with patch("openai_client.ServiceConfig") as MockServiceConfig:
            MockServiceConfig.return_value = mock_service_config
            context_transfer_config = ContextTransferConfigModel(service_config=mock_service_config)
            assert context_transfer_config.track_progress is False

    @patch("openai_client.ServiceConfig", MagicMock())
    def test_template_specific_prompts(self):
        """Test that templates use different prompt text."""
        # Create mock service config
        mock_service_config = MagicMock()
        mock_service_config.service_type = "openai"

        # Default template has project assistant prompt
        with patch("openai_client.ServiceConfig") as MockServiceConfig:
            MockServiceConfig.return_value = mock_service_config
            default_config = AssistantConfigModel(service_config=mock_service_config)
            assert "project assistant" in default_config.instruction_prompt.lower()

        # Context transfer template has context transfer prompt
        with patch("openai_client.ServiceConfig") as MockServiceConfig:
            MockServiceConfig.return_value = mock_service_config
            context_transfer_config = ContextTransferConfigModel(service_config=mock_service_config)
            assert "context transfer" in context_transfer_config.instruction_prompt.lower()

    @patch("openai_client.ServiceConfig", MagicMock())
    def test_template_specific_welcome_messages(self):
        """Test that templates use different welcome messages."""
        # Create mock service config
        mock_service_config = MagicMock()
        mock_service_config.service_type = "openai"

        # Default template coordinator welcome message
        with patch("openai_client.ServiceConfig") as MockServiceConfig:
            MockServiceConfig.return_value = mock_service_config
            default_config = AssistantConfigModel(service_config=mock_service_config)
            assert (
                "personal conversation as the project coordinator"
                in default_config.coordinator_config.welcome_message.lower()
            )

        # Context transfer template coordinator welcome message
        with patch("openai_client.ServiceConfig") as MockServiceConfig:
            MockServiceConfig.return_value = mock_service_config
            context_transfer_config = ContextTransferConfigModel(service_config=mock_service_config)
            assert "knowledge bridge" in context_transfer_config.coordinator_config.welcome_message.lower()
