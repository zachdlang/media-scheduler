
DROP FUNCTION IF EXISTS follows_episode(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION follows_episode(_watcherid INTEGER, _episodeid INTEGER) RETURNS BOOLEAN AS $$
DECLARE 
BEGIN
	-- Only care about episodes not marked as watched
	RETURN EXISTS(SELECT * FROM watcher_episode WHERE watched = false AND watcherid = _watcherid AND episodeid = _episodeid);
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS follows_tvshow(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION follows_tvshow(_watcherid INTEGER, _tvshowid INTEGER) RETURNS BOOLEAN AS $$
DECLARE 
BEGIN
	RETURN EXISTS(SELECT * FROM watcher_tvshow WHERE watcherid = _watcherid AND tvshowid = _tvshowid);
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS add_watcher_tvshow(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION add_watcher_tvshow(_watcherid INTEGER, _tvshowid INTEGER) RETURNS VOID AS $$
DECLARE 
BEGIN
	IF follows_tvshow(_watcherid, _tvshowid) = false THEN
		INSERT INTO watcher_tvshow (watcherid, tvshowid) VALUES (_watcherid, _tvshowid);
	END IF;
	RETURN;
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS remove_watcher_tvshow(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION remove_watcher_tvshow(_watcherid INTEGER, _tvshowid INTEGER) RETURNS VOID AS $$
DECLARE 
BEGIN
	DELETE FROM watcher_tvshow WHERE watcherid = _watcherid AND tvshowid = _tvshowid;
	RETURN;
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS mark_episode_watched(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION mark_episode_watched(_watcherid INTEGER, _episodeid INTEGER) RETURNS VOID AS $$
DECLARE
BEGIN
	UPDATE watcher_episode SET watched = true WHERE watcherid = _watcherid AND episodeid = _episodeid;
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS episode_populate_watcher_episodes();
CREATE OR REPLACE FUNCTION episode_populate_watcher_episodes() RETURNS TRIGGER AS $$
DECLARE
	rec RECORD;
BEGIN
	FOR rec in (SELECT * FROM watcher_tvshow WHERE tvshowid = NEW.tvshowid)
	LOOP
		INSERT INTO watcher_episode (episodeid, watcherid) VALUES (NEW.id, rec.watcherid);
	END LOOP;
	RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS episode_populate_watcher_episodes ON episode CASCADE;
CREATE TRIGGER episode_populate_watcher_episodes AFTER INSERT ON episode FOR EACH ROW EXECUTE PROCEDURE episode_populate_watcher_episodes();


DROP FUNCTION IF EXISTS watcher_tvshow_populate_watcher_episodes();
CREATE OR REPLACE FUNCTION watcher_tvshow_populate_watcher_episodes() RETURNS TRIGGER AS $$
DECLARE
	rec RECORD;
	in_past BOOLEAN;
BEGIN
	FOR rec IN (SELECT * FROM episode WHERE tvshowid = NEW.tvshowid)
	LOOP
		in_past = rec.airdate < current_date;
		INSERT INTO watcher_episode (episodeid, watcherid, watched) VALUES (rec.id, NEW.watcherid, in_past);
	END LOOP;
	RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS watcher_tvshow_populate_watcher_episodes ON watcher_tvshow CASCADE;
CREATE TRIGGER watcher_tvshow_populate_watcher_episodes AFTER INSERT ON watcher_tvshow FOR EACH ROW EXECUTE PROCEDURE watcher_tvshow_populate_watcher_episodes();


DROP FUNCTION IF EXISTS watcher_tvshow_remove_watcher_episodes();
CREATE OR REPLACE FUNCTION watcher_tvshow_remove_watcher_episodes() RETURNS TRIGGER as $$
DECLARE
BEGIN
	DELETE FROM watcher_episode WHERE episodeid IN (SELECT id FROM episode WHERE tvshowid = OLD.tvshowid) AND watcherid = OLD.watcherid;
	RETURN OLD;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS watcher_tvshow_remove_watcher_episodes ON watcher_tvshow CASCADE;
CREATE TRIGGER watcher_tvshow_remove_watcher_episodes AFTER DELETE ON watcher_tvshow FOR EACH ROW EXECUTE PROCEDURE watcher_tvshow_remove_watcher_episodes();
