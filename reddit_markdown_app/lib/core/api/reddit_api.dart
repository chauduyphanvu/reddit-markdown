import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/post.dart';
import '../models/comment.dart';

class RedditApiException implements Exception {
  final String message;
  RedditApiException(this.message);
}

class RedditApi {
  static const String _baseUrl = 'https://www.reddit.com';

  Future<(Post, List<Comment>)> fetchPost(String url) async {
    final jsonUrl = url.endsWith('.json') ? url : url + '.json';

    try {
      final response = await http.get(Uri.parse(jsonUrl));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final post = Post.fromJson(data[0]);
        final comments = (data[1]['data']['children'] as List)
            .where((reply) => reply['kind'] == 't1')
            .map((reply) => Comment.fromJson(reply))
            .toList();
        return (post, comments);
      } else {
        throw RedditApiException('Failed to load post. Status code: ${response.statusCode}');
      }
    } catch (e) {
      throw RedditApiException('Failed to fetch post: $e');
    }
  }
}

