class Comment {
  final String author;
  final String body;
  final int ups;
  final DateTime createdUtc;
  final List<Comment> replies;

  Comment({
    required this.author,
    required this.body,
    required this.ups,
    required this.createdUtc,
    this.replies = const [],
  });

  factory Comment.fromJson(Map<String, dynamic> json) {
    final data = json['data'];
    final repliesData = data['replies'];

    return Comment(
      author: data['author'] ?? '[deleted]',
      body: data['body'] ?? '[deleted]',
      ups: data['ups'] ?? 0,
      createdUtc: DateTime.fromMillisecondsSinceEpoch((data['created_utc'] ?? 0).toInt() * 1000),
      replies: repliesData is Map<String, dynamic> && repliesData['data']?['children'] != null
          ? (repliesData['data']['children'] as List)
              .where((reply) => reply['kind'] == 't1')
              .map((reply) => Comment.fromJson(reply))
              .toList()
          : [],
    );
  }
}

