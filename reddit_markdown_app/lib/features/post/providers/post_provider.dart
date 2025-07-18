import 'package:flutter/material.dart';
import '../../../core/api/reddit_api.dart';
import '../../../core/models/post.dart';
import '../../../core/models/comment.dart';

enum PostStatus { initial, loading, success, error }

class PostProvider with ChangeNotifier {
  final RedditApi _redditApi = RedditApi();

  Post? _post;
  List<Comment> _comments = [];
  PostStatus _status = PostStatus.initial;
  String _errorMessage = '';

  Post? get post => _post;
  List<Comment> get comments => _comments;
  PostStatus get status => _status;
  String get errorMessage => _errorMessage;

  Future<void> fetchPost(String url) async {
    _status = PostStatus.loading;
    notifyListeners();

    try {
      final (post, comments) = await _redditApi.fetchPost(url);
      _post = post;
      _comments = comments;
      _status = PostStatus.success;
    } on RedditApiException catch (e) {
      _errorMessage = e.message;
      _status = PostStatus.error;
    } catch (e) {
      _errorMessage = 'An unknown error occurred.';
      _status = PostStatus.error;
    }
    notifyListeners();
  }
}

