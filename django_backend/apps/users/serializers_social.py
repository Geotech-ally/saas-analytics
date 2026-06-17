from rest_framework import serializers


class SocialJWTResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

