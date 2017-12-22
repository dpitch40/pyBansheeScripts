CREATE TABLE CoreConfiguration (
                    EntryID             INTEGER PRIMARY KEY,
                    Key                 TEXT,
                    Value               TEXT
                );
CREATE TABLE CorePrimarySources (
                    PrimarySourceID     INTEGER PRIMARY KEY,
                    StringID            TEXT UNIQUE,
                    CachedCount         INTEGER,
                    IsTemporary         INTEGER DEFAULT 0
                );
CREATE TABLE CoreTracks (
                    PrimarySourceID     INTEGER NOT NULL,
                    TrackID             INTEGER PRIMARY KEY,
                    ArtistID            INTEGER,
                    AlbumID             INTEGER,
                    TagSetID            INTEGER,
                    ExternalID          INTEGER,

                    MusicBrainzID       TEXT,

                    Uri                 TEXT,
                    MimeType            TEXT,
                    FileSize            INTEGER,
                    BitRate             INTEGER,
                    SampleRate          INTEGER,
                    BitsPerSample       INTEGER,
                    Attributes          INTEGER DEFAULT 5,
                    LastStreamError     INTEGER DEFAULT 0,

                    Title               TEXT,
                    TitleLowered        TEXT,
                    TitleSort           TEXT,
                    TitleSortKey        BLOB,
                    TrackNumber         INTEGER,
                    TrackCount          INTEGER,
                    Disc                INTEGER,
                    DiscCount           INTEGER,
                    Duration            INTEGER,
                    Year                INTEGER,
                    Genre               TEXT,
                    Composer            TEXT,
                    Conductor           TEXT,
                    Grouping            TEXT,
                    Copyright           TEXT,
                    LicenseUri          TEXT,

                    Comment             TEXT,
                    Rating              INTEGER,
                    Score               INTEGER,
                    PlayCount           INTEGER,
                    SkipCount           INTEGER,
                    LastPlayedStamp     INTEGER,
                    LastSkippedStamp    INTEGER,
                    DateAddedStamp      INTEGER,
                    DateUpdatedStamp    INTEGER,
                    MetadataHash        TEXT,
                    BPM                 INTEGER,
                    LastSyncedStamp     INTEGER,
                    FileModifiedStamp   INTEGER
                );
CREATE INDEX CoreTracksPrimarySourceIndex ON CoreTracks(ArtistID, AlbumID, PrimarySourceID, Disc, TrackNumber, Uri);
CREATE INDEX CoreTracksAggregatesIndex ON CoreTracks(FileSize, Duration);
CREATE INDEX CoreTracksExternalIDIndex ON CoreTracks(PrimarySourceID, ExternalID);
CREATE INDEX CoreTracksUriIndex ON CoreTracks(PrimarySourceID, Uri);
CREATE INDEX CoreTracksCoverArtIndex ON CoreTracks (PrimarySourceID, AlbumID, DateUpdatedStamp);
CREATE TABLE CoreAlbums (
                    AlbumID             INTEGER PRIMARY KEY,
                    ArtistID            INTEGER,
                    TagSetID            INTEGER,

                    MusicBrainzID       TEXT,

                    Title               TEXT,
                    TitleLowered        TEXT,
                    TitleSort           TEXT,
                    TitleSortKey        BLOB,

                    ReleaseDate         INTEGER,
                    Duration            INTEGER,
                    Year                INTEGER,
                    IsCompilation       INTEGER DEFAULT 0,

                    ArtistName          TEXT,
                    ArtistNameLowered   TEXT,
                    ArtistNameSort      TEXT,
                    ArtistNameSortKey   BLOB,

                    Rating              INTEGER,

                    ArtworkID           TEXT
                );
CREATE INDEX CoreAlbumsIndex ON CoreAlbums(ArtistID, TitleSortKey);
CREATE INDEX CoreAlbumsArtistIndex ON CoreAlbums(TitleSortKey, ArtistNameSortKey);
CREATE TABLE CoreArtists (
                    ArtistID            INTEGER PRIMARY KEY,
                    TagSetID            INTEGER,
                    MusicBrainzID       TEXT,
                    Name                TEXT,
                    NameLowered         TEXT,
                    NameSort            TEXT,
                    NameSortKey         BLOB,
                    Rating              INTEGER
                );
CREATE INDEX CoreArtistsIndex ON CoreArtists(NameSortKey);
CREATE TABLE CorePlaylists (
                    PrimarySourceID     INTEGER,
                    PlaylistID          INTEGER PRIMARY KEY,
                    Name                TEXT,
                    SortColumn          INTEGER NOT NULL DEFAULT -1,
                    SortType            INTEGER NOT NULL DEFAULT 0,
                    Special             INTEGER NOT NULL DEFAULT 0,
                    CachedCount         INTEGER,
                    IsTemporary         INTEGER DEFAULT 0
                );
CREATE TABLE CorePlaylistEntries (
                    EntryID             INTEGER PRIMARY KEY,
                    PlaylistID          INTEGER NOT NULL,
                    TrackID             INTEGER NOT NULL,
                    ViewOrder           INTEGER NOT NULL DEFAULT 0,
                    Generated           INTEGER NOT NULL DEFAULT 0
                );
CREATE INDEX CorePlaylistEntriesIndex ON CorePlaylistEntries(PlaylistID, TrackID);
CREATE TABLE CoreSmartPlaylists (
                    PrimarySourceID     INTEGER,
                    SmartPlaylistID     INTEGER PRIMARY KEY,
                    Name                TEXT NOT NULL,
                    Condition           TEXT,
                    OrderBy             TEXT,
                    LimitNumber         TEXT,
                    LimitCriterion      TEXT,
                    CachedCount         INTEGER,
                    IsTemporary         INTEGER DEFAULT 0,
                    IsHiddenWhenEmpty   INTEGER DEFAULT 0
                );
CREATE TABLE CoreSmartPlaylistEntries (
                    EntryID             INTEGER PRIMARY KEY,
                    SmartPlaylistID     INTEGER NOT NULL,
                    TrackID             INTEGER NOT NULL
                );
CREATE INDEX CoreSmartPlaylistEntriesIndex ON CoreSmartPlaylistEntries(SmartPlaylistID, TrackID);
CREATE TABLE CoreRemovedTracks (
                    TrackID             INTEGER NOT NULL,
                    Uri                 TEXT,
                    DateRemovedStamp    INTEGER
                );
CREATE TABLE CoreCacheModels (
                    CacheID             INTEGER PRIMARY KEY,
                    ModelID             TEXT
                );
CREATE TABLE CoreShuffles (
                    ShufflerId           INTEGER,
                    TrackID             INTEGER,
                    LastShuffledAt      INTEGER,
                    CONSTRAINT one_entry_per_track UNIQUE (ShufflerID, TrackID)
                );
CREATE INDEX CoreShufflesIndex ON CoreShuffles (ShufflerId, TrackID, LastShuffledAt);
CREATE TABLE CoreShufflers (
                    ShufflerId      INTEGER PRIMARY KEY,
                    Id              TEXT UNIQUE
                );
CREATE TABLE CoreShuffleModifications (
                    ShufflerId           INTEGER,
                    TrackID              INTEGER,
                    LastModifiedAt       INTEGER,
                    ModificationType     INTEGER,
                    CONSTRAINT one_entry_per_track UNIQUE (ShufflerID, TrackID)
                );
CREATE INDEX CoreShuffleModificationsIndex ON CoreShuffleModifications (ShufflerId, TrackID, LastModifiedAt, ModificationType);
CREATE TABLE CoverArtDownloads (
                        AlbumID     INTEGER UNIQUE,
                        Downloaded  BOOLEAN,
                        LastAttempt INTEGER NOT NULL
                    );
CREATE TABLE LastfmStations (
                        StationID           INTEGER PRIMARY KEY,
                        Creator             STRING NOT NULL,
                        Name                STRING NOT NULL,
                        Type                STRING NOT NULL,
                        Arg                 STRING NOT NULL,
                        PlayCount           INTEGER NOT NULL
                    );
CREATE TABLE IaItems (
                        ItemID         INTEGER PRIMARY KEY,
                        ID             TEXT UNIQUE NOT NULL,
                        Title          TEXT NOT NULL,
                        MediaType      TEXT,
                        DetailsJson    TEXT,

                        SelectedFormat TEXT,
                        BookmarkFile   TEXT,
                        BookmarkPosition INTEGER DEFAULT 0
                    );
CREATE TABLE HyenaModelVersions (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE,
                        version INTEGER);
CREATE TABLE PodcastSyndications(last_auto_download INTEGER,AutoDownload INTEGER,DownloadStatus INTEGER,IsSubscribed INTEGER,FeedID INTEGER PRIMARY KEY,Title TEXT,Description TEXT,Url TEXT,Keywords TEXT,Category TEXT,Copyright TEXT,ImageUrl TEXT,UpdatePeriodMinutes INTEGER,Language TEXT,LastDownloadError INTEGER,LastDownloadTime INTEGER,Link TEXT,MaxItemCount INTEGER,PubDate INTEGER,LastBuildDate INTEGER,SyncSetting INTEGER);
CREATE INDEX PodcastSyndicationsIndex ON PodcastSyndications (IsSubscribed, Title);
CREATE TABLE PodcastItems(FeedID INTEGER,LicenseUri TEXT,ItemID INTEGER PRIMARY KEY,Author TEXT,Comments TEXT,Description TEXT,StrippedDescription TEXT,Guid TEXT,IsRead INTEGER,Link TEXT,Modified INTEGER,PubDate INTEGER,Title TEXT,Active INTEGER);
CREATE INDEX PodcastItemsFeedIDIndex ON PodcastItems(FeedID);
CREATE INDEX PodcastItemsGuidIndex ON PodcastItems(Guid);
CREATE INDEX PodcastItemIsReadIndex ON PodcastItems(IsRead);
CREATE TABLE PodcastEnclosures(ItemID INTEGER,EnclosureID INTEGER PRIMARY KEY,LocalPath TEXT,Url TEXT,Keywords TEXT,Duration INTEGER,FileSize INTEGER,MimeType TEXT,DownloadedAt INTEGER,DownloadStatus INTEGER);
CREATE INDEX PodcastEnclosuresItemIDIndex ON PodcastEnclosures(ItemID);
CREATE TABLE Bookmarks(BookmarkId INTEGER PRIMARY KEY,Position INTEGER,CreatedAt INTEGER,Type TEXT,TrackId INTEGER);
CREATE TABLE MetadataProblems (
                        ProblemID   INTEGER PRIMARY KEY,
                        ProblemType TEXT NOT NULL,
                        TypeOrder   INTEGER NOT NULL,
                        Generation  INTEGER NOT NULL,
                        Selected    INTEGER DEFAULT 1,

                        SolutionValue       TEXT,
                        SolutionOptions     TEXT,
                        ObjectIds   TEXT,
                        ObjectCount INTEGER,

                        UNIQUE (ProblemType, Generation, ObjectIds) ON CONFLICT IGNORE
                    );
