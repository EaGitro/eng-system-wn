import sqlite3
import spacy  # as a lemmatizer
import sys, re
from flask import Flask, g, request
from flask_cors import CORS


from wordlist import Wordlist
"""en_core_web_md install
python -m spacy download en_core_web_md
"""


"""返すべき値
[{
    "単語": word,
    "品詞": pos,
    "Synsets": [
        {
            synset_id: str,
            definitions : {
                int: {
                    jpn: str,
                    eng: str
                }
            }
            examples: [
                eng: str,
                jpn: str
            ], 
            
            word_synset_freq: int,          # その word がその synset で使われる頻度 
            syno_list: list[synset_id:str, word_id:int, word:str, lang:str, freq:int]    # synonym word list
        },
    ]
}]
"""

"""各テーブルスキーマ
sense
CREATE TABLE sense (
                          synset text,      # synset_id
                          wordid integer,   # 
                          lang text,
                          rank text,
                          lexid integer,
			              freq integer,
                          src text)

synset_def                          
CREATE TABLE synset_def (
                          synset text,  # synset_id
			              lang text,    # jpn/eng
			              def text,     # 定義(and example)
                          sid text)     # 複数ある場合の区別

synset_ex                          
CREATE TABLE synset_ex (  synset text,  # synset_id
			              lang text,    # jpn/eng
                          def text,     # 例文
                          sid text)     # 複数ある場合の区別

word
CREATE TABLE word (       wordid integer primary key,
                          lang text,
                          lemma text,
                          pron text,
                          pos text)                         
"""




            

# def get_cur(dbpath):
#     if "cur" not in g:
#         g.cur=sqlite3.connect(dbpath).cursor()
#     return g.cur


class Wnjp:
    def __init__(self, nlp, dbpath) -> None:
        self.nlp = nlp
        self.cur = sqlite3.connect(dbpath).cursor()

    def get_wordids_and_pos(self, lemma:str)->list[any]:
        """lemma を受け取り wordid と pos の配列を返す.
        ただし lemma は配列ではないことに注意。 see: words2wordids
        """
        self.cur.execute(
            """
            SELECT wordid, pos FROM word
            WHERE lemma = ? AND lang = ?
            """, (lemma, "eng")
        )
        w_tmp = self.cur.fetchall()

        return w_tmp
    
    def get_synsetids_and_synsetword_freq(self, wordid):
        """wordid を受け取り、synsetid と freq が含まれたリストを返す。
        ~~ただし freq が1以上のもののみを返す~~。0でも返す.
        
        Returns:
            [
                [synsetid, freq],
            ]
        """
        self.cur.execute(
            """
            SELECT synset, freq FROM sense
            WHERE wordid = ? AND lang = ? AND freq >= ?
            """, (wordid, "eng", 0)
        )

        s_tmp = self.cur.fetchall()

        return s_tmp
    
    def get_defs(self,synsetid:str):
        """synsetid を受け取り、definition が含まれた辞書を返す

        Returns:
            返値の例:
            {
                0: {
                    "eng": "an idea that is suggested",
                    "jpn": "提案される考え"
                }
            }
        """
        print("synsetid", synsetid)
        self.cur.execute(
            """
            SELECT def, lang, sid FROM synset_def
            WHERE synset = ? 
            """, ((synsetid,))
        )

        defs_tmp = self.cur.fetchall()
        dobj={}
        """
        dobj = {
            sid: {
                lang: def
            } 
        }

        example:
        {
            0: {
                eng: an idea that is suggested,
                jpn: 提案される考え
            }
        }
        """
        print(defs_tmp)
        for d in defs_tmp:
            # dobj.append({"def":d[0], "lang": d[1], "sid": d[2]})
            # print(d)
            # print(type(d))
            # print(d[2])
            # print(type(d[2]))
            if d[2] in dobj:
                dobj[d[2]][d[1]] = d[0]         # jpn:"jpn-def"
            else:
                dobj[d[2]] = {d[1]: d[0]}
        return dobj

    def get_examples(self, synsetid, lemma):
        """synsetid を受け取り、そこに合致する例文を lemmatize し、lemmaが含まれる例文を返す """

        self.cur.execute(
            """
            SELECT lang, def, sid FROM synset_ex
            WHERE synset = ?
            """, ((synsetid,))
        )

        examples_tmp = self.cur.fetchall()
        matched_sids = []
        matched_exens = {}
        exjps = {}

        examples = []
        

        for ex in examples_tmp:
            if ex[0] == "eng":
                exen = ex[1]
                
                # lemmatize example
                doc = nlp(exen)
                lemmatized_text = [token.lemma_ for token in doc]
                
                if lemma in lemmatized_text:
                    matched_sids.append(ex[2])
                    matched_exens[ex[2]]=exen

            else:
                exjps[ex[2]] = ex[1]

        for sid in matched_sids:
            examples.append({"eng": matched_exens[sid], "jpn": exjps.get(sid, "")})
        
        return examples

    def get_lemma_from_wordid(self, wordid:int)->str:
        self.cur.execute(
            """
            SELECT lemma FROM word
            WHERE wordid = ?
            """, ((wordid,))
        )
        lemma = self.cur.fetchall()[0][0]
        return lemma
    
    def get_synos(self, synsetid, wordid)->list[str]:
        """synsetid を受け取り、そのsynosetの語として含まれている語の内、 wordid が wordid でないものをリストで返す。
        ~~ただし freq が1以上のもののみ~~。 0 でも返す
        """
        self.cur.execute(
            """
            SELECT wordid, freq FROM sense
            WHERE synset = ? and lang = ? and freq >= ? and wordid <> ?
            """, ((synsetid, "eng", 0, wordid))
        )

        synosobj_tmp = self.cur.fetchall()
        synosobj = []
        for syno in synosobj_tmp:
            lemma = self.get_lemma_from_wordid(syno[0])
            synosobj.append({"wordid": syno[0], "word": lemma, "freq": syno[1]})

        return synosobj


    def wordids2words(self, wordids:list[int])->dict[any]:
        """wordid の配列を受け取り、 {wordid: word} のオブジェクトを返す。
        """
        wordid_list_str = ", ".join(f"{wordid}" for wordid in wordids)
        print(wordid_list_str)
        self.cur.execute(
            f"""
            SELECT wordid, lemma, pos FROM word
            WHERE wordid in ({wordid_list_str})
            """
            # (("wordid_list_str",))
        )

        lemmas_tmp = self.cur.fetchall()
        # print(lemmas_tmp)
        words_and_wordids={}
        for item in lemmas_tmp:
            words_and_wordids[item[0]]={"word": item[1].replace("_", " "), "pos":item[2]}

        print(words_and_wordids)
        return words_and_wordids
    

    def synsetids2synsetdefs(self, synsetids:list[str])->list[any]:
        """synsetid の配列を受け取り、以下のオブジェクトを返す。

        [
        {
            synsetid: [
                {
                    eng: str,
                    jpn: str
                },
            ]
        },
        ] 
        """

        synsets = {}
        for synsetid in synsetids:
            self.cur.execute(
                """
                SELECT synset, lang, def, sid FROM synset_def
                WHERE synset = ?
                """,
                ((synsetid,))
            )
            synsetids_tmp = self.cur.fetchall()
            synsetdefs_tmp = [{"eng": "", "jpn": ""} for _ in range(20)]
            print(synsetdefs_tmp)
            sid_max = 0
            for synsetdef in synsetids_tmp:     # synset, lang, def, sid
                # synset = synsetdef[0]
                lang = synsetdef[1]
                def_ = synsetdef[2]
                sid = int(synsetdef[3])
                synsetdefs_tmp[sid][lang] = def_
                sid_max = max(sid_max,sid)
                
            print(synsetdefs_tmp)
            print(synsetdefs_tmp[0:sid_max+1])
            tmp = synsetdefs_tmp[0:sid_max+1]
            synsets[synsetid] = tmp
            print(synsets[synsetid])

        return synsets

    def synsetids2synos(self, synsetids:list[str], n:int, lang:str)->list[any]:
        """synsetid の配列を受け取り、それをキーとして、その synset に属する最初のn個のlang語の単語を返す
        """
        obj = {key: {"eng": [], "jpn": []} for key in synsetids}
        where_in_query = "'"+"', '".join(synsetids)+"'"
        print(where_in_query)
        self.cur.execute(
            (f"""
            SELECT synset, wordid, lang, lemma
            FROM (
                SELECT synset, sense.wordid, sense.lang, word.lemma,
                    ROW_NUMBER() OVER (PARTITION BY synset) AS rownum
                FROM sense
                INNER JOIN word ON sense.wordid = word.wordid
                WHERE synset IN ({where_in_query})
                AND sense.lang = "{lang}"
            )
            WHERE rownum <= {n};
            """) 
            # ((where_in_query,n))
        )

        rows = self.cur.fetchall()
        # if lang == "jpn":
        #     self.cur.execute(
        #         f"""
        #         SELECT synset, wordid, lang, lemma
        #         FROM (
        #             SELECT synset, sense.wordid, sense.lang, word.lemma,
        #                 ROW_NUMBER() OVER (PARTITION BY synset) AS rownum
        #             FROM sense
        #             INNER JOIN word ON sense.wordid = word.wordid
        #             WHERE synset IN ({where_in_query})
        #             AND sense.lang = "eng"
        #         )
        #         WHERE rownum <= {n};
        #         """
        #     )
        # row.append(self.cur.fetchall())
        print(rows)
        for row in rows:    # synset, wordid, lang, lemma
            obj[row[0]][row[2]].append(row[3])
        print(obj)
        new_query = ""
        for k,v in obj.items():
            print(k,v, v["jpn"])
            if len(v["jpn"])==0:
                new_query += f"'{k}',"
                print(new_query)
         
        if len(new_query) != 0:
            new_query = new_query[:-1]
            self.cur.execute(
                f"""
                SELECT synset, wordid, lang, lemma
                FROM (
                    SELECT synset, sense.wordid, sense.lang, word.lemma,
                        ROW_NUMBER() OVER (PARTITION BY synset) AS rownum
                    FROM sense
                    INNER JOIN word ON sense.wordid = word.wordid
                    WHERE synset IN ({new_query})
                    AND sense.lang = "eng"
                )
                WHERE rownum <= {n};
                """
            )
            rows = self.cur.fetchall()
            print(rows)
            for row in rows:    # synset, wordid, lang, lemma
                obj[row[0]][row[2]].append(row[3])
            print(obj)
        retObj = {}
        for k,v in obj.items():
            retObj[k] = v["jpn"]+v["eng"]
        return retObj
    

    def wordid2lemma_and_pos(self, wordid:int) -> dict[str,str]:
        """wordid を受け取り {lemma: str, pos: str} を返す"""
        retobj = {}
        self.cur.execute(
            f"""
            SELECT wordid, lemma, pos FROM word
            WHERE wordid = {wordid}
            """
        )
        lemma_pos = self.cur.fetchall() # [wordid, lemma, pos]
        retobj["lemma"] = lemma_pos[0][1]
        retobj["pos"] = lemma_pos[0][2]

        print(retobj)

        return retobj

    def words2wordids(self, words:list[str])->list[int,str]:
        """word の配列を受け取り、 [word, wordid, pos] の配列を返す"""
        
        lemmas_obj = {}
        lemmas_str = ""
        for word in words:
            # print("nlp:",nlp(word), "\tstr(nlp):", str(nlp(word)), "\ttype:", type(nlp(word)))
            lemmas_obj[str(nlp(word))] = word

        lemmas_str = "'" + "', '".join(lemmas_obj.keys()) + "'"
        # print(lemmas_str)
        self.cur.execute(
            f"""
            SELECT lemma, wordid, pos FROM word
            WHERE lemma in ({lemmas_str}) 
            """
        )
        wordids_tmp = self.cur.fetchall()
        res = [[lemmas_obj[lemma], wordid, pos] for lemma, wordid, pos in wordids_tmp if lemma in lemmas_obj]

        return res


    def synset2freq_wordid(self, synsetid:str) -> list[dict[str,int]]:
        """synsetdi を受け取り {freq:int, wordid:int}[] を返す"""
        self.cur.execute(
            f"""
            SELECT freq, wordid FROM sense
            WHERE synset = "{synsetid}" AND lang = "eng"
            """
        )
        t = self.cur.fetchall()
        freq_sum = 0
        res = []
        for freq, wordid in t:
            freq_sum += freq
            res.append({"freq": freq, "wordid": wordid})

        return {"words": res, "sum":freq_sum}


# target_word = sys.argv[1]
targets=["idea", "move", "dead", "happy", "ignore"]
# wnjp = Wordnetjp("./db/wnjpn.db")

# wordids = wnjp.get_wordids_from_lemma(
#         wnjp.lemmatize(
#             target_word
#         )
#     )
# print(wordids)
# print(
#     wnjp.get_synsetids_from_wordid(wordids[0])
# )

# for t in targets: 
#     print("target:",t)
#     wnjp.get_synsetobjs_from_lemma(t)


app = Flask(__name__)
CORS(app)
nlp = spacy.load('en_core_web_md')
# wnjp=Wnjp(nlp, "./db/wnjpn.db")

# print(dir(app))
# print(dir(app.template_global))
# wnjp = Wordnetjp("./db/wnjpn.db")

def get_wnjp():
    if "wnjp" not in g:
        g.wnjp = Wnjp(nlp,"./db/wnjpn.db")
    return g.wnjp


@app.route("/w/<string:word>")
def get_word(word):

    lemma = word
    wnjp=get_wnjp()
    wi_p=wnjp.wordid2lemma_and_pos(lemma)
    print("get_wordids_and_pos==========", wi_p)
    res = []
    for w in wi_p:
        wid = w[0]
        pos = w[1]
        synsets = []
        for synsetid, freq in wnjp.get_synsetids_and_synsetword_freq(w[0]):
            synsetobj={"synsetid":synsetid, "freq":freq}
            synsetobj["defs"] = wnjp.get_defs(synsetid)
            synsetobj["examples"] = wnjp.get_examples(synsetid, lemma)
            synsetobj["syno_list"] = wnjp.get_synos(synsetid, wid)
            synsets.append(synsetobj)
            

        res.append({"wordid": w[0], "pos": w[1], "synsets": synsets})
    return res
# wnjp.close_db()

@app.route("/tmp-learning-words", defaults={"level":0})
@app.route("/tmp-learning-words/", defaults={"level":0})
@app.route("/tmp-learning-words/<int:level>")
def tmp_learing_words(level):

    match level:
        case 2000:
            r = Wordlist.w2000
        case 3000:
            r = Wordlist.w3000
        case 5000:
            r = Wordlist.w5000

        case 2010:
            r = Wordlist.w2000

        case 10000:
            r = Wordlist.w10000

        case 1 | 2 | 3:
            r = sum(Wordlist.common_words[level],[])
        case _:
            r = ['test', 'theme', 'trial', 'swing', 'operate']

    return r



@app.route("/wordids2words", methods=["POST"])
def wordids2words():
    """wordid の配列を受け取り、 {wordid:{word:str, pos:str}} のオブジェクトを返す。

    {
        wordid: {
            word: string,
            pos: "a" | "r" | "n" | "v"
        }
    }
    """
    wnjp=get_wnjp()
    req = request.json
    print("====wordids2words====")
    return wnjp.wordids2words(req)

@app.route("/synsetids2synsetdefs", methods=["POST"])
def synsetids2synsetdefs():
    """synsetid の配列を受け取り、以下のオブジェクトを返す。

    [
    {
        synsetid: [
            {
                eng: str,
                jpn: str
            },
        ]
    },
    ] 
    """

    wnjp = get_wnjp()
    req = request.json

    return wnjp.synsetids2synsetdefs(req)

@app.route("/synsetids2synos", methods=["POST"])
def synsetids2synos():
    """synsetid の配列を受け取り、それをキーとして、その synset に属する最初のsynoNum個のlang語の単語を返す
    
    POST されるべき JSON の型は:
    {
        "synoNum"?: int,                // default: 2
        "lang"?: "jpn" | "eng"          // default: "jpn"
        "synsetids": str[]          
    }
    """
    wnjp=get_wnjp()
    req = request.json
    return wnjp.synsetids2synos(req["synsetids"],req.get("synoNum") or 2, req.get("lang") or "jpn")


@app.route("/wid/<int:wid>")
def wordid2wordobj(wid):
    """wordid を受け取り、`/w/<word>` の中でその wordid に当たるもののみを返す"""
    
    wnjp=get_wnjp()
    lemma_pos = wnjp.wordid2lemma_and_pos(wid)
    lemma = lemma_pos["lemma"]
    pos = lemma_pos["pos"]
    synsets = []
    for synsetid, freq in wnjp.get_synsetids_and_synsetword_freq(wid):
        synsetobj={"synsetid":synsetid, "freq":freq}
        synsetobj["defs"] = wnjp.get_defs(synsetid)
        synsetobj["examples"] = wnjp.get_examples(synsetid, lemma)
        synsetobj["syno_list"] = wnjp.get_synos(synsetid, wid)
        synsets.append(synsetobj)
            

    res = {"wordid": wid, "pos": pos, "synsets": synsets, "word": lemma }

    return res


@app.route("/words2wordids", methods=["POST"])
def words2wordids():
    """word の配列を受け取り、 [word, wordid, pos] の配列を返す"""
    wnjp=get_wnjp()
    req = request.json
    res = wnjp.words2wordids(req)

    return res


@app.route("/synset2freq-wordid/<string:synsetid>")
def synsetinfo(synsetid):
    """synsetid を受け取り以下を返す
    
    {
        words: {freq:int, wordid:int},
        sum: int
    }
    """
    wnjp=get_wnjp()
    res = wnjp.synset2freq_wordid(synsetid)
    return res



if __name__ == "__main__":
    app.run()