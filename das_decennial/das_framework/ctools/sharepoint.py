#
# Some Human's Sharepoint implementation


# This is how you can read from sharepoint with Windows Domain authentication.
# This is a stub


def sharepoint_broken() -> None:
    import win32com.client

    url = 'https://....'

    h = win32com.client.Dispatch('WinHTTP.WinHTTPRequest.5.1')
    h.SetAutoLogonPolicy(0)
    h.Open('GET', url, False)
    h.Send()
    result = h.responseText
