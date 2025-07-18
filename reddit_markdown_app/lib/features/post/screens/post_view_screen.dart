import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import '../providers/post_provider.dart';
import '../widgets/comment_widget.dart';
import '../../settings/providers/settings_provider.dart';

class PostViewScreen extends StatelessWidget {
  const PostViewScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final postProvider = Provider.of<PostProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(postProvider.post?.subreddit ?? 'Post'),
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: () {
              final post = postProvider.post;
              if (post != null) {
                final markdown = '# ${post.title}\n\n${post.selftext}';
                Share.share(markdown, subject: post.title);
              }
            },
          ),
        ],
      ),
      body: Consumer<PostProvider>(
        builder: (context, provider, child) {
          if (provider.status == PostStatus.loading) {
            return const Center(child: CircularProgressIndicator());
          } else if (provider.status == PostStatus.success && provider.post != null) {
            final post = provider.post!;
            return ListView(
              padding: const EdgeInsets.all(16.0),
              children: [
                Text(post.title, style: Theme.of(context).textTheme.headlineMedium).animate().fadeIn(duration: 300.ms).slideX(),
                const SizedBox(height: 8),
                Text('by ${post.author} in ${post.subreddit}', style: Theme.of(context).textTheme.titleSmall).animate().fadeIn(duration: 300.ms, delay: 100.ms).slideX(),
                const Divider(height: 32),
                if (post.selftext.isNotEmpty)
                  MarkdownBody(data: post.selftext, selectable: true).animate().fadeIn(duration: 300.ms, delay: 200.ms),
                const Divider(height: 32),
                Text('${post.numComments} Comments', style: Theme.of(context).textTheme.headlineSmall).animate().fadeIn(duration: 300.ms, delay: 300.ms).slideX(),
                const SizedBox(height: 16),
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: provider.comments.length,
                  itemBuilder: (context, index) {
                    return CommentWidget(comment: provider.comments[index])
                        .animate()
                        .fadeIn(duration: 300.ms, delay: (400 + index * 50).ms);
                  },
                ),
              ],
            );
          } else {
            return Center(child: Text(provider.errorMessage));
          }
        },
      ),
    );
  }
}

