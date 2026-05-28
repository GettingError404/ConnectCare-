from pipeline.nlp_hybrid import NLPEngine
from pipeline.action_handler import ActionHandler
from pipeline.response_generator import ResponseGenerator
from pipeline.sentiment import SentimentAnalyzer

class ChatAgent:
    def __init__(self, config):
        self.nlp = NLPEngine(config["nlp"])
        self.actions = ActionHandler()
        self.response_gen = ResponseGenerator()
        self.sentiment = SentimentAnalyzer()

        # Agent is stateless. Conversation context must be provided by
        # external persistence/retrieval services (ConversationContextService).

    def process(self, user_id: str, message: str, context: list | None = None):
        """Process a user message and return an agent response.

        Parameters:
        - user_id: identifier for the user (for logging/audit)
        - message: the incoming user message text
        - context: optional list of prior message dicts provided by the
          ConversationContextService. Example: [{"user":..., "bot":...}, ...]

        The agent does not persist or cache conversations locally. Persistence
        and retrieval are the responsibility of backend services.
        """
        # 1. Context
        context = context or []

        # 2. NLP
        nlp_result = self.nlp.process(message)

        intent = nlp_result.get("intent")
        entities = nlp_result.get("entities", {})

        # 3. Sentiment
        sentiment = self.sentiment.analyze(message)

        # 4. Action execution
        action_result = self.actions.handle(intent, entities)

        # 5. Response generation
        response = self.response_gen.generate(
            intent=intent,
            action_result=action_result,
            sentiment=sentiment,
            context=context
        )

        # Do NOT store context locally - return response and let caller persist.
        return {
            "response": response,
            "intent": intent,
            "sentiment": sentiment,
            "action_data": action_result
        }