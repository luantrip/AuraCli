## Aura Monitor - HTTP Client
## ==========================
##
## Lightweight HTTP client for fetching web content.
## Designed for terminal browser use cases.
##
## Features:
## - HTTP/HTTPS GET requests
## - Redirect following
## - Custom headers
## - Timeout handling
## - Content-Type detection

{.push raises: [].}

import std/[httpclient, net, uri, strutils, options, os]
import monitor_types

type
  FetchError* = enum
    feNone
    feTimeout
    feConnectionFailed
    feDnsError
    feSslError
    feRedirectLoop
    feInvalidUrl
    feUnknown

  FetchResult* = object
    success*: bool
    error*: FetchError
    errorMessage*: string
    statusCode*: int
    contentType*: ContentType
    charset*: string
    content*: string
    headers*: seq[tuple[key, value: string]]
    finalUrl*: string
    redirectCount*: int

  FetchOptions* = object
    timeout*: int # Seconds
    followRedirects*: bool
    maxRedirects*: int
    userAgent*: string
    extraHeaders*: seq[tuple[key, value: string]]
    cookies*: seq[tuple[name, value: string]]

proc defaultFetchOptions*(): FetchOptions =
  result.timeout = 30
  result.followRedirects = true
  result.maxRedirects = 10
  result.userAgent = "AuraMonitor/" & MONITOR_VERSION

proc detectContentType*(headers: HttpHeaders; url: string): ContentType =
  ## Detect content type from headers or URL
  var ct = ""
  try:
    let ctValues = headers.getOrDefault("Content-Type")
    if ctValues.len > 0:
      ct = $ctValues[0]
  except:
    ct = ""

  if "text/html" in ct:
    return ctHtml
  elif "text/markdown" in ct or "text/x-markdown" in ct:
    return ctMarkdown
  elif "application/json" in ct:
    return ctJson
  elif "text/gemini" in ct:
    return ctGemini
  elif "text/plain" in ct:
    return ctPlain

  # Fallback to URL extension
  let path = parseUri(url).path
  if path.endsWith(".html") or path.endsWith(".htm"):
    return ctHtml
  elif path.endsWith(".md") or path.endsWith(".markdown"):
    return ctMarkdown
  elif path.endsWith(".json"):
    return ctJson
  elif path.endsWith(".gmi"):
    return ctGemini

  return ctPlain

proc extractCharset*(contentType: string): string =
  ## Extract charset from Content-Type header
  result = "utf-8" # Default

  if "charset=" in contentType:
    let parts = contentType.split("charset=")
    if parts.len > 1:
      result = parts[1].strip.strip(chars = {'"', '\''}).split(';')[0].strip

proc fetch*(url: string; options: FetchOptions = defaultFetchOptions()): FetchResult =
  ## Fetch content from a URL
  result.success = false
  result.error = feNone
  result.finalUrl = url

  # Validate URL
  var parsedUrl: Uri
  try:
    parsedUrl = parseUri(url)
    if parsedUrl.scheme == "":
      # Try adding https://
      parsedUrl = parseUri("https://" & url)
      result.finalUrl = $parsedUrl
  except:
    result.error = feInvalidUrl
    result.errorMessage = "Invalid URL format"
    return

  if parsedUrl.scheme notin ["http", "https"]:
    result.error = feInvalidUrl
    result.errorMessage = "Only HTTP and HTTPS are supported"
    return

  # Create client
  var client: HttpClient
  try:
    client = newHttpClient(
      timeout = options.timeout * 1000,
      userAgent = options.userAgent
    )

    # SSL context is handled automatically by httpclient

    # Set extra headers
    for header in options.extraHeaders:
      client.headers[header.key] = header.value

    # Set cookies
    if options.cookies.len > 0:
      var cookieStr = ""
      for cookie in options.cookies:
        if cookieStr != "":
          cookieStr &= "; "
        cookieStr &= cookie.name & "=" & cookie.value
      client.headers["Cookie"] = cookieStr

    # Perform request with redirect handling
    var currentUrl = result.finalUrl
    var redirectCount = 0

    while true:
      let response = client.get(currentUrl)

      result.statusCode = response.code.int

      # Collect headers
      for key, value in response.headers:
        result.headers.add((key, value))

      # Handle redirects
      if response.code in {Http301, Http302, Http303, Http307, Http308}:
        if not options.followRedirects:
          break

        inc redirectCount
        if redirectCount > options.maxRedirects:
          result.error = feRedirectLoop
          result.errorMessage = "Too many redirects"
          return

        let locationValues = response.headers.getOrDefault("Location")
        let location = if locationValues.len > 0: $locationValues[0] else: ""
        if location == "":
          break

        # Resolve relative URL
        if location.startsWith("/"):
          currentUrl = $parsedUrl.scheme & "://" & parsedUrl.hostname & location
        elif not location.startsWith("http"):
          let baseUrl = $parsedUrl.scheme & "://" & parsedUrl.hostname &
              parsedUrl.path.rsplit('/', 1)[0] & "/"
          currentUrl = baseUrl & location
        else:
          currentUrl = location

        result.finalUrl = currentUrl
        result.redirectCount = redirectCount
        continue

      # Success or non-redirect status
      result.content = response.body
      result.contentType = detectContentType(response.headers, currentUrl)
      let ctHeaderValues = response.headers.getOrDefault("Content-Type")
      let ctHeader = if ctHeaderValues.len > 0: $ctHeaderValues[0] else: ""
      result.charset = extractCharset(ctHeader)
      result.success = response.code.int in 200..299
      break

  except TimeoutError:
    result.error = feTimeout
    result.errorMessage = "Request timed out"
  except SslError:
    result.error = feSslError
    result.errorMessage = "SSL/TLS error"
  except OSError as e:
    result.error = feDnsError
    result.errorMessage = "DNS or connection error: " & e.msg
  except:
    result.error = feUnknown
    result.errorMessage = "Unknown error: " & getCurrentExceptionMsg()
  finally:
    if client != nil:
      try:
        client.close()
      except:
        discard

# Async version removed - can be added later if needed with asyncdispatch import

# =============================================================================
# FILE PROTOCOL
# =============================================================================

proc fetchFile*(path: string): FetchResult =
  ## Fetch content from local file
  result.success = false
  result.finalUrl = "file://" & path

  let expandedPath = expandTilde(path)

  if not fileExists(expandedPath):
    result.error = feUnknown
    result.errorMessage = "File not found: " & path
    return

  try:
    result.content = readFile(expandedPath)
    result.success = true
    result.statusCode = 200

    # Detect content type from extension
    if path.endsWith(".html") or path.endsWith(".htm"):
      result.contentType = ctHtml
    elif path.endsWith(".md") or path.endsWith(".markdown"):
      result.contentType = ctMarkdown
    elif path.endsWith(".json"):
      result.contentType = ctJson
    elif path.endsWith(".gmi"):
      result.contentType = ctGemini
    else:
      result.contentType = ctPlain

    result.charset = "utf-8"
  except:
    result.error = feUnknown
    result.errorMessage = "Error reading file: " & getCurrentExceptionMsg()

# =============================================================================
# UNIFIED FETCH
# =============================================================================

proc fetchUrl*(url: string; options: FetchOptions = defaultFetchOptions()): FetchResult =
  ## Fetch content from URL or file path
  if url.startsWith("file://"):
    result = fetchFile(url[7 .. ^1])
  elif url.startsWith("/") or url.startsWith("~"):
    result = fetchFile(url)
  else:
    result = fetch(url, options)
