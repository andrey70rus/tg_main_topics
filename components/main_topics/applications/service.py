import pandas as pd
from datetime import timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords

import spacy

from adapters.dto import DateTopics


class KeyWordsQualifier:
    def __init__(self):
        self.lemmatize_pipeline = spacy.load('ru_core_news_sm')

    def key_words_by_days(self, messages_df: pd.DataFrame) -> DateTopics:
        # There are a lot of channels based on Moscow/EU timezone
        messages_df['datetime_GMT3'] = pd.to_datetime(
            messages_df['datetime'] + timedelta(hours=3)
        )
        messages_df['date'] = messages_df['datetime_GMT3'].dt.normalize()
        days_messages = messages_df[['date', 'text']]
        days_messages = self._filter_none_text(days_messages)
        tf_idf_importance = self._calc_tf_idf(days_messages)
        top_list = self.get_top_words(tf_idf_importance)

        print(top_list)
        ...


    @staticmethod
    def get_top_words(word_importance: pd.DataFrame):
        top_list = []

        # word_importance.index - it is date (without time)
        top_words = word_importance.groupby(word_importance.index).sum()

        for row_idx, row in top_words.iterrows():
            top_list.append(
                DateTopics(
                    date=row_idx,
                    top_keywords=row.sort_values(ascending=False).head(15)
                )
            )

        return top_list

    @staticmethod
    def _filter_none_text(df: pd.DataFrame):
        return df[df['text'] != '']

    def _calc_tf_idf(self, df: pd.DataFrame):
        # логика: 1. смотрим значимость того или иного слова для каждой новости
        #  2. по самым значимым словам считаем сумму tf-idf внутри дня
        #  3. выводим топ слов для каждого дня

        # Лематизация - вытащим нормальные формы слов из текстов, для обучения
        stop_words = set(stopwords.words('russian'))

        vectorizer = TfidfVectorizer(
            ngram_range=(1, 3), max_df=0.5, max_features=1000,
        )

        df['preproc_text'] = self._preproc_lemmatize(df['text'], stop_words)

        vectors = vectorizer.fit_transform(df['preproc_text'])
        word_importance = pd.DataFrame(
            data=vectors.toarray(), columns=vectorizer.get_feature_names_out(),
            index=df['date']
        )

        return word_importance

    def _preproc_lemmatize(self, text_series: pd.Series, stop_words=set()):
        new_texts = {}
        for idx, msg in zip(text_series.index, self.lemmatize_pipeline.pipe(
                text_series.values, batch_size=64, n_process=4
        )):
            new_texts[idx] = ' '.join(
                [tok.lemma_.lower() for tok in msg if tok.lemma_.lower()
                 not in stop_words and len(tok.lemma_) > 2]
            )

        return pd.Series(new_texts)
