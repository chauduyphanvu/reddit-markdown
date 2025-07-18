class Post {
  final String title;
  final String author;
  final String subreddit;
  final String selftext;
  final int ups;
  final int numComments;
  final String url;
  final DateTime createdUtc;

  Post({
    required this.title,
    required this.author,
    required this.subreddit,
    required this.selftext,
    required this.ups,
    required this.numComments,
    required this.url,
    required this.createdUtc,
  });

  factory Post.fromJson(Map<String, dynamic> json) {
    final data = json['data']['children'][0]['data'];
    return Post(
      title: data['title'],
      author: data['author'],
      subreddit: data['subreddit_name_prefixed'],
      selftext: data['selftext'],
      ups: data['ups'],
      numComments: data['num_comments'],
      url: data['url'],
      createdUtc: DateTime.fromMillisecondsSinceEpoch(data['created_utc'].toInt() * 1000),
    );
  }
}

