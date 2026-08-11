from allauth.account.adapter import DefaultAccountAdapter


class EmailOnlyAccountAdapter(DefaultAccountAdapter):
    """Allauth adapter that skips username population.

    Our User model uses email-only authentication and has no ``username``
    field.  The default ``DefaultAccountAdapter.populate_username`` method
    would attempt to write to that missing field, causing
    ``FieldError: 'User' has no field named 'username'``.
    """

    def populate_username(self, request, user):
        # Do nothing — our User model has no username field.
        pass