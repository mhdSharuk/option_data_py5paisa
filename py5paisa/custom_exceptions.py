class InvalidLoginCredentialsException(Exception):
  pass

class InvalidFutureExpiryDateException(Exception):
  pass

class InvalidLoginException(Exception):
  pass

class FetchExpiryException(Exception):
  pass

class InvalidOptionExpiryDateException(Exception):
  pass

class OptionChainFetchException(Exception):
  pass

class SpotFetchException(Exception):
  pass

class FuturesFetchException(Exception):
  pass