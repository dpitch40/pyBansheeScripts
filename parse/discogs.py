import config
import discogs_client

global _discogs_client
_discogs_client = None

def get_client():
    global _discogs_client

    if _discogs_client is None:
        _discogs_client = discogs_client.Client(config.DiscogsAppName, user_token=config.DiscogsUserToken)

    return _discogs_client

def main():
    d = get_client()

    results = d.search('William Basinski', type='artist')
    print(results.pages)
    for release in results[0].releases:
        if release.data['role'] == 'Main':
            print(release.data['title'], release.data['artist'], release.data['year'], release.data['role'])
        else:
            break

if __name__ == '__main__':
    main()
