"""Token utilities for password reset.

Uses Django's built-in PasswordResetTokenGenerator pattern (memory-safe, hash-based).
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator


password_reset_token_generator = PasswordResetTokenGenerator()

