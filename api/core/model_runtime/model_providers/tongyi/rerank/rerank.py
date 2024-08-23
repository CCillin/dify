from typing import Optional

import dashscope
from dashscope.common.error import (
    AuthenticationError,
    InvalidParameter,
    RequestFailure,
    ServiceUnavailableError,
    UnsupportedHTTPMethod,
    UnsupportedModel,
)

from core.model_runtime.entities.rerank_entities import RerankDocument, RerankResult
from core.model_runtime.errors.invoke import (
    InvokeAuthorizationError,
    InvokeBadRequestError,
    InvokeConnectionError,
    InvokeError,
    InvokeRateLimitError,
    InvokeServerUnavailableError,
)
from core.model_runtime.errors.validate import CredentialsValidateFailedError
from core.model_runtime.model_providers.__base.rerank_model import RerankModel
from core.model_runtime.model_providers.tongyi._common import _CommonTongyi

class TongyiRerankModel(_CommonTongyi,RerankModel):
    def _invoke(
        self, 
        model: str, 
        credentials: dict,
        query: str, 
        docs: list[str], 
        score_threshold: Optional[float] = None, 
        top_n: Optional[int] = None,
        user: Optional[str] = None
    ) -> RerankResult:
        credentials_kwargs = self._to_credential_kwargs(credentials)
        
        if len(docs) == 0:
            return RerankResult(model=model, docs=[])
        
        response = dashscope.TextReRank.call(
            model=model,
            query=query,
            documents=docs,
            top_n=top_n,
            return_documents=True,
            api_key=credentials_kwargs["dashscope_api_key"],
        )

        results = response.output

        rerank_documents = []
        for result in results['results']:
            rerank_document = RerankDocument(
                index=result['index'],
                text=result['document']['text'],
                score=result['relevance_score'],
            )
            if score_threshold is None or result['relevance_score'] >= score_threshold:
                rerank_documents.append(rerank_document)

        return RerankResult(model=model, docs=rerank_documents)

    def validate_credentials(self, model: str, credentials: dict) -> None:
        try:

            self._invoke(
                model=model,
                credentials=credentials,
                query="What is the capital of the United States?",
                docs=[
                    "Carson City is the capital city of the American state of Nevada. At the 2010 United States "
                    "Census, Carson City had a population of 55,274.",
                    "The Commonwealth of the Northern Mariana Islands is a group of islands in the Pacific Ocean that "
                    "are a political division controlled by the United States. Its capital is Saipan.",
                ],
                score_threshold=0.8
            )
        except Exception as ex:
            raise CredentialsValidateFailedError(str(ex))


    @property
    def _invoke_error_mapping(self) -> dict[type[InvokeError], list[type[Exception]]]:
        """
        Map model invoke error to unified error
        The key is the error type thrown to the caller
        The value is the error type thrown by the model,
        which needs to be converted into a unified error type for the caller.

        :return: Invoke error mapping
        """
        return {
            InvokeConnectionError: [
                RequestFailure,
            ],
            InvokeServerUnavailableError: [
                ServiceUnavailableError,
            ],
            InvokeRateLimitError: [],
            InvokeAuthorizationError: [
                AuthenticationError,
            ],
            InvokeBadRequestError: [
                InvalidParameter,
                UnsupportedModel,
                UnsupportedHTTPMethod,
            ]
        }