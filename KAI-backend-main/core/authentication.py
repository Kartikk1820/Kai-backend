from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        pw_hash = validated_token.get('pw_hash')
        if pw_hash and pw_hash != user.password[-10:]:
            raise AuthenticationFailed('Password has changed. Please log in again.')
        return user
