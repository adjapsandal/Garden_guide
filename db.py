import os
import logging
import psycopg2
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
_conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASS'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT')
)


@contextmanager
def get_cursor(write: bool = False):
    cur = _conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        if write:
            _conn.commit()
    except Exception:
        _conn.rollback()
        logger.exception("Ошибка SQL-запроса")
        raise
    finally:
        cur.close()


def get_subjects():
    with get_cursor() as cur:
        cur.execute("""
            SELECT s.subject_name, s.subject_num
                FROM subjects s
            ORDER BY s.subject_name;
        """)
        return cur.fetchall()


def get_region(subject_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT r.region_num, r.region_name
              FROM region r
              JOIN subjects s
                ON s.fk_region_num = r.region_num
             WHERE s.subject_num = %s;
        """, (subject_num,))
        return cur.fetchone()


def get_plant_types(region_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT pt.plant_type_num, pt.plant_type_name
                FROM plant_type pt
                JOIN crop c  ON c.fk_plant_type_num = pt.plant_type_num
                JOIN crop_region cr ON cr.fk_crop_num = c.crop_num
            WHERE cr.fk_region_num = %s
            ORDER BY pt.plant_type_name;
        """, (region_num,))
        return cur.fetchall()


def get_crops(region_num: int, plant_type_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT c.crop_num, c.crop_name
                FROM crop c
                JOIN crop_region cr ON cr.fk_crop_num = c.crop_num
            WHERE cr.fk_region_num = %s
                AND c.fk_plant_type_num = %s
            ORDER BY c.crop_name;
        """, (region_num, plant_type_num))
        return cur.fetchall()


def get_sorts(region_num: int, crop_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT s.plant_num, s.plant_name, s.plant_image_url, c.crop_name
                FROM sort s
                INNER JOIN sort_region sr ON s.plant_num = sr.fk_plant_num
                INNER JOIN crop c ON s.fk_crop_num = c.crop_num
            WHERE s.fk_crop_num = %s
                AND sr.fk_region_num = %s
            ORDER BY s.plant_name ASC;
        """, (crop_num, region_num))
        return cur.fetchall()


def get_sort_details(region_num: int, plant_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT 
                s.plant_num, 
                s.plant_name, 
                c.crop_name,
                s.plant_image_url,
                COALESCE(sr.region_feature, cr.region_feature) AS details,
                COALESCE(sr.region_date_seed, cr.region_date_seed) AS date_seed,
                COALESCE(sr.region_date_harvest, cr.region_date_harvest) AS date_harvest
            FROM 
                sort s
            JOIN crop c ON s.fk_crop_num = c.crop_num
            LEFT JOIN sort_region sr ON s.plant_num = sr.fk_plant_num AND sr.fk_region_num = %s
            LEFT JOIN crop_region cr ON s.fk_crop_num = cr.fk_crop_num AND cr.fk_region_num = %s
            WHERE 
                s.plant_num = %s;
        """, (region_num, region_num, plant_num)
        )
        return cur.fetchone()


def get_user_favourites(user_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT fk_plant_num
              FROM user_favourite_plant
             WHERE fk_user_num = %s;
        """, (user_num,)
        )
        rows = cur.fetchall()
        return [row['fk_plant_num'] for row in rows]


def add_favourite(user_num: int, plant_num: int):
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO user_favourite_plant (fk_user_num, fk_plant_num)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """, (user_num, plant_num)
        )


def remove_favourite(user_num: int, plant_num: int):
    with get_cursor(write=True) as cur:
        cur.execute("""
            DELETE FROM user_favourite_plant
             WHERE fk_user_num = %s AND fk_plant_num = %s;
        """, (user_num, plant_num)
        )


def get_favourite_plants(user_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT s.plant_num,
                   s.plant_name,
                   s.plant_feature,
                   s.plant_image_url,
                   c.crop_name
              FROM sort s
              JOIN user_favourite_plant ufp
                ON ufp.fk_plant_num = s.plant_num
              JOIN crop c
                ON c.crop_num = s.fk_crop_num
             WHERE ufp.fk_user_num = %s;
        """, (user_num,)
        )
        return cur.fetchall()


def get_agronomist_by_user(user_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.agronomist_num,
                   a.agronomist_name,
                   a.agronomist_degree,
                   a.fk_region_num,
                   r.region_name
              FROM agronomist a
              JOIN region r ON a.fk_region_num = r.region_num
             WHERE a.fk_user_num = %s;
        """, (user_num,))
        return cur.fetchone()


def add_sort(plant_name: str, fk_crop_num: int, plant_feature: str, plant_image_url: str) -> int:
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO sort (plant_name, fk_crop_num, plant_feature, plant_image_url)
            VALUES (%s, %s, %s, %s)
            RETURNING plant_num;
        """, (plant_name, fk_crop_num, plant_feature, plant_image_url))
        row = cur.fetchone()
        return row['plant_num'] if row else None


def get_crops_for_region(region_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT c.crop_num, c.crop_name, cr.region_feature
              FROM crop c
              JOIN crop_region cr ON cr.fk_crop_num = c.crop_num
             WHERE cr.fk_region_num = %s
             ORDER BY c.crop_name;
        """, (region_num,))
        return cur.fetchall()


def get_sorts_for_region(region_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT s.plant_num, s.plant_name, sr.region_feature
              FROM sort s
              JOIN sort_region sr ON sr.fk_plant_num = s.plant_num
             WHERE sr.fk_region_num = %s
             ORDER BY s.plant_name;
        """, (region_num,))
        return cur.fetchall()


def add_crop_region(region_num: int, crop_num: int, region_feature: str):
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO crop_region (fk_region_num, fk_crop_num, region_feature)
            VALUES (%s, %s, %s);
        """, (region_num, crop_num, region_feature))


def update_crop_region(region_num: int, crop_num: int, region_feature: str):
    with get_cursor(write=True) as cur:
        cur.execute("""
            UPDATE crop_region
               SET region_feature = %s
             WHERE fk_region_num = %s
               AND fk_crop_num = %s;
        """, (region_feature, region_num, crop_num))


def delete_crop_region(region_num: int, crop_num: int):
    with get_cursor(write=True) as cur:
        cur.execute("""
            DELETE FROM crop_region
             WHERE fk_region_num = %s
               AND fk_crop_num = %s;
        """, (region_num, crop_num))


def add_sort_region(region_num: int, plant_num: int, region_feature: str):
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO sort_region (fk_region_num, fk_plant_num, region_feature)
            VALUES (%s, %s, %s);
        """, (region_num, plant_num, region_feature))


def update_sort_region(region_num: int, plant_num: int, region_feature: str):
    with get_cursor(write=True) as cur:
        cur.execute("""
            UPDATE sort_region
               SET region_feature = %s
             WHERE fk_region_num = %s
               AND fk_plant_num = %s;
        """, (region_feature, region_num, plant_num))


def delete_sort_region(region_num: int, plant_num: int):
    with get_cursor(write=True) as cur:
        cur.execute("""
            DELETE FROM sort_region
             WHERE fk_region_num = %s
               AND fk_plant_num = %s;
        """, (region_num, plant_num))


def get_pests():
    with get_cursor() as cur:
        cur.execute("""
            SELECT pest_num, pest_name, pest_feature
              FROM pest
             ORDER BY pest_name;
        """)
        return cur.fetchall()


def add_pest(pest_name: str, pest_feature: str) -> int: 
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO pest (pest_name, pest_feature)
            VALUES (%s, %s)
            RETURNING pest_num;
        """, (pest_name, pest_feature))
        row = cur.fetchone()
        return row['pest_num'] if row else None


def get_crop_pests(crop_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT p.pest_num, p.pest_name, p.pest_feature
              FROM pest p
              JOIN crop_pest cp ON cp.fk_pest_num = p.pest_num
             WHERE cp.fk_crop_num = %s;
        """, (crop_num,))
        return cur.fetchall()


def add_crop_pest(crop_num: int, pest_num: int):
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO crop_pest (fk_crop_num, fk_pest_num)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """, (crop_num, pest_num))


def update_crop_pest(crop_num: int, old_pest_num: int, new_pest_num: int):
    with get_cursor(write=True) as cur:
        cur.execute("""
            UPDATE crop_pest
               SET fk_pest_num = %s
             WHERE fk_crop_num = %s
               AND fk_pest_num = %s;
        """, (new_pest_num, crop_num, old_pest_num))


def delete_crop_pest(crop_num: int, pest_num: int):
    with get_cursor(write=True) as cur:
        cur.execute("""
            DELETE FROM crop_pest
             WHERE fk_crop_num = %s
               AND fk_pest_num = %s;
        """, (crop_num, pest_num))


def get_all_plant_types():
    with get_cursor() as cur:
        cur.execute("""
            SELECT plant_type_num, plant_type_name
              FROM plant_type
             ORDER BY plant_type_name;
        """)
        return cur.fetchall()


def get_all_crops():
    with get_cursor() as cur:
        cur.execute("""
            SELECT crop_num, crop_name
              FROM crop
             ORDER BY crop_name;
        """)
        return cur.fetchall()


def get_all_sorts():
    with get_cursor() as cur:
        cur.execute("""
            SELECT plant_num, plant_name
              FROM sort
             ORDER BY plant_name;
        """)
        return cur.fetchall()


def add_crop_with_region(region_num: int, crop_name: str, plant_type_num: int, region_feature: str, region_date_seed: str, region_date_harvest: str) -> int:
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO crop (crop_name, fk_plant_type_num)
            VALUES (%s, %s)
            RETURNING crop_num;
        """, (crop_name, plant_type_num))
        row = cur.fetchone()
        if not row:
            raise ValueError("Failed to insert crop.")
        new_crop_num = row['crop_num']
        cur.execute("""
            INSERT INTO crop_region (fk_region_num, fk_crop_num, region_feature, region_date_seed, region_date_harvest)
            VALUES (%s, %s, %s, %s, %s);
        """, (region_num, new_crop_num, region_feature, region_date_seed, region_date_harvest))
        return new_crop_num


def get_articles():
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.article_num, a.article_name, a.article_text, u.user_name
              FROM article a
              JOIN "user" u ON a.fk_user_num = u.user_num
             ORDER BY a.article_date DESC;
        """)
        return cur.fetchall()


def add_article(article_name: str, article_text: str, user_num: int) -> int:
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO article (article_name, article_text, article_date, fk_user_num)
            VALUES (%s, %s, CURRENT_DATE, %s)
            RETURNING article_num;
        """, (article_name, article_text, user_num))
        row = cur.fetchone()
        return row['article_num'] if row else None


def get_article(article_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.article_num, a.article_name, a.article_text, a.article_date, u.user_name
              FROM article a
              JOIN "user" u ON a.fk_user_num = u.user_num
             WHERE a.article_num = %s;
        """, (article_num,))
        return cur.fetchone()


def get_comments(article_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT c.comment_num, c.comment_text, c.comment_date, u.user_name
              FROM comment c
              JOIN "user" u ON c.fk_user_num = u.user_num
             WHERE c.fk_article_num = %s
             ORDER BY c.comment_date ASC;
        """, (article_num,))
        return cur.fetchall()


def add_comment(article_num: int, comment_text: str, user_num: int) -> int:
    with get_cursor(write=True) as cur:
        cur.execute("""
            INSERT INTO comment (comment_text, comment_date, fk_article_num, fk_user_num)
            VALUES (%s, CURRENT_DATE, %s, %s)
            RETURNING comment_num;
        """, (comment_text, article_num, user_num))
        row = cur.fetchone()
        return row['comment_num'] if row else None


def get_user_articles(user_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT article_num, article_name, article_text, article_date
            FROM article
            WHERE fk_user_num = %s
            ORDER BY article_date DESC;
        """, (user_num,))
        return cur.fetchall()


def delete_article(article_num: int):
    with get_cursor(write=True) as cur:
        cur.execute("""
            DELETE FROM article
            WHERE article_num = %s;
        """, (article_num,))


def update_article(article_num: int, article_name: str, article_text: str):
    with get_cursor(write=True) as cur:
        cur.execute("""
            UPDATE article
               SET article_name = %s, article_text = %s
             WHERE article_num = %s;
        """, (article_name, article_text, article_num))


def get_crop_pest_details(crop_num: int, pest_num: int):
    with get_cursor() as cur:
        cur.execute("""
            SELECT cp.details, p.pest_name, p.pest_feature
              FROM crop_pest cp
              JOIN pest p ON cp.fk_pest_num = p.pest_num
             WHERE cp.fk_crop_num = %s AND cp.fk_pest_num = %s;
        """, (crop_num, pest_num))
        return cur.fetchone()
