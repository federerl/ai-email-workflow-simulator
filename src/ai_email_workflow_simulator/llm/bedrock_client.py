"""Thin wrapper around the Bedrock Runtime `converse` API.

Uses `converse` rather than `invoke_model` because it's a stable,
model-family-agnostic interface -- no need to hand-roll the Anthropic-specific
request/response body shape.
"""

import boto3
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    NoRegionError,
    ProfileNotFound,
)

from .. import config
from .mock_responses import mock_converse

_client = None


class BedrockConfigError(RuntimeError):
    """Raised when Bedrock is not configured/accessible."""


def get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
    return _client


def converse(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    if config.MOCK_LLM:
        return mock_converse(system_prompt, user_prompt)

    if not config.BEDROCK_MODEL_ID:
        raise BedrockConfigError(
            "BEDROCK_MODEL_ID is not set. Copy .env.example to .env and set a "
            "model id enabled for your AWS account/region."
        )

    try:
        client = get_client()
        response = client.converse(
            modelId=config.BEDROCK_MODEL_ID,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
        )
    except (NoCredentialsError, ProfileNotFound, NoRegionError) as exc:
        raise BedrockConfigError(
            f"AWS credentials/config problem ({type(exc).__name__}): {exc}. "
            "Configure credentials via `aws configure`, AWS_ACCESS_KEY_ID/"
            "AWS_SECRET_ACCESS_KEY env vars, or an AWS_PROFILE in .env that "
            "matches a profile in ~/.aws/config."
        ) from exc
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("AccessDeniedException", "ValidationException"):
            raise BedrockConfigError(
                f"Bedrock call failed ({code}). Confirm model "
                f"'{config.BEDROCK_MODEL_ID}' is enabled for your account/region "
                "-- check `aws bedrock list-foundation-models`."
            ) from exc
        raise

    return response["output"]["message"]["content"][0]["text"]
