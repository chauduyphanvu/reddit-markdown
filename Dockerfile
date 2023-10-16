FROM ruby:3.2-alpine

WORKDIR /app

COPY *.rb ./
COPY settings.json ./
COPY Gemfile ./

RUN bundle install

ENTRYPOINT [ "ruby", "./reddit_markdown.rb" ]
