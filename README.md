


```sh

python -m spacy download en_core_web_md
```

```python
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
```

