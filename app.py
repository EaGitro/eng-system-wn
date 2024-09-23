import sqlite3
import spacy  # as a lemmatizer
import sys, re
from flask import Flask, g


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
        }
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
        ただし freq が1以上のもののみを返す
        
        Returns:
            [
                [synsetid, freq],
            ]
        """
        self.cur.execute(
            """
            SELECT synset, freq FROM sense
            WHERE wordid = ? AND lang = ? AND freq >= ?
            """, (wordid, "eng", 1)
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
    wi_p=wnjp.get_wordids_and_pos(lemma)
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

if __name__ == "__main__":
    app.run(debug=True)